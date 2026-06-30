// GET /api/evidence-search?ingredient_id=omega3  (또는 &q=term)
// PubMed(NCBI E-utilities)로 성분 관련 최신 논문을 검색 — 근거 '원문 링크' 보강.
//  키 불필요(NCBI_API_KEY 있으면 rate↑). 배포환경 실데이터, 샌드박스/오류는 source:'none'.
import ingredientsData from '../../../data/ingredients.json';

export const runtime = 'nodejs';

const byId = Object.fromEntries(ingredientsData.ingredients.map((i) => [i.id, i]));
const EUTILS = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils';
const keyParam = () => (process.env.NCBI_API_KEY ? `&api_key=${process.env.NCBI_API_KEY}` : '');

async function j(url) {
  const res = await fetch(url, { headers: { accept: 'application/json' } });
  if (!res.ok) throw new Error('NCBI ' + res.status);
  return res.json();
}

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const id = searchParams.get('ingredient_id');
  const ing = id ? byId[id] : null;
  const base = searchParams.get('q') || (ing ? ing.name_en : '');
  if (!base) return Response.json({ error: 'ingredient_id 또는 q가 필요합니다.' }, { status: 400 });

  // 보충제 맥락 + 임상 우선
  const term = `${base} supplementation AND (randomized controlled trial[pt] OR meta-analysis[pt] OR systematic review[pt])`;
  try {
    const es = await j(`${EUTILS}/esearch.fcgi?db=pubmed&retmode=json&sort=relevance&retmax=5&term=${encodeURIComponent(term)}${keyParam()}`);
    const ids = es?.esearchresult?.idlist || [];
    if (!ids.length) return Response.json({ ingredient_id: id || null, query: base, source: 'pubmed', total: 0, articles: [] });
    const sum = await j(`${EUTILS}/esummary.fcgi?db=pubmed&retmode=json&id=${ids.join(',')}${keyParam()}`);
    const r = sum?.result || {};
    const articles = ids.map((pmid) => {
      const a = r[pmid] || {};
      return {
        pmid,
        title: a.title || '(제목 미상)',
        journal: a.fulljournalname || a.source || '',
        pubdate: a.pubdate || '',
        url: `https://pubmed.ncbi.nlm.nih.gov/${pmid}/`,
      };
    }).filter((a) => a.title && a.title !== '(제목 미상)');
    return Response.json({
      ingredient_id: id || null, query: base, source: 'pubmed',
      total: Number(es?.esearchresult?.count || articles.length), articles,
      note: 'PubMed 임상연구(RCT·메타분석·체계적고찰) 우선 검색 결과. 제목·저널 클릭 시 원문.',
    });
  } catch (e) {
    return Response.json({ ingredient_id: id || null, query: base, source: 'none', total: null, articles: [], reason: e.message });
  }
}
