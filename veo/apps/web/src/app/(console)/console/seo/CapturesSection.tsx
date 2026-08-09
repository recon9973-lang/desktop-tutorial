import { Card, EmptyState, ErrorState, formatCount } from '@veo/ui';

import { readCaptures, type FetchCapture } from '@/lib/scan-report';

import own from './seo.module.css';

/**
 * 원자료 — **판정 말고, 우리가 실제로 받은 것.**
 *
 * ## 왜 이 화면이 생겼나
 *
 * 서버는 처음부터 이것을 남기고 있었다. 화면만 없었다
 * (`audit/2026-08-08-server-ui-gap.md` §B — *"판정은 보이는데 무엇을 받아서 그렇게
 * 판정했는지는 화면에서 못 본다"*). 그 자리가 없어서 venomad 진단의 원인을 확정하는 데
 * 하루가 들었다(`seo/schemas.py:250`).
 *
 * 거래처가 "이 점수 이상한데요" 라고 할 때 열 자리다. 우리 판정을 변호하는 것이 아니라
 * **무엇을 보고 그렇게 판정했는지 그대로 보여 주는** 자리다. 우리가 틀렸으면 여기서
 * 드러난다.
 *
 * ## 지키는 것
 *
 * **본문을 HTML 로 그리지 않는다.** 남의 사이트에서 받아 온 글자다. 그리는 순간 그 안의
 * 스크립트가 우리 콘솔에서 돈다. `<pre>` 안에 글자로만 넣는다 — React 가 기본으로
 * 이스케이프하고, 이 파일 어디에도 `dangerouslySetInnerHTML` 이 없다.
 *
 * **못 읽은 것이 앞에 온다.** 서버가 그 순서로 준다. 200 응답 스무 개 뒤에 숨은 403
 * 하나가 점수를 끌어내리는 자리이고, 그것이 맨 아래 있으면 아무도 못 본다.
 *
 * **새로 재지 않는다.** 저장된 것만 읽는다 — 이 화면을 여는 것이 거래처 서버를 두드리는
 * 일이 되면 안 된다.
 */
export async function CapturesSection({ scanRunId }: { readonly scanRunId: string }) {
  const found = await readCaptures(scanRunId);

  if (!found.ok) {
    return (
      <ErrorState
        title="원자료를 불러오지 못했습니다"
        description={
          found.message ??
          '이 진단은 받은 응답이 남아 있지 않습니다. 다시 측정하면 이후로는 그대로 열립니다.'
        }
      />
    );
  }

  const { captures, noteKo } = found.data;

  if (captures.length === 0) {
    return (
      <EmptyState
        title="남아 있는 응답이 없습니다"
        description={noteKo || '이 진단보다 앞선 판에서는 원자료를 저장하지 않았습니다.'}
      />
    );
  }

  const failed = captures.filter((one) => one.readFailureKo !== null).length;

  return (
    <section className={own.captures} aria-label="진단이 받은 응답">
      <p className={own.capturesNote}>
        {noteKo}
        {' · 응답 '}
        {formatCount(captures.length)}건
        {failed > 0 ? ` · 문서로 읽지 못한 것 ${formatCount(failed)}건` : ''}
      </p>

      {captures.map((capture) => (
        <CaptureCard key={`${capture.url}-${capture.contentHash}`} capture={capture} />
      ))}
    </section>
  );
}

function CaptureCard({ capture }: { readonly capture: FetchCapture }) {
  const failed = capture.readFailureKo !== null;

  return (
    <Card
      title={capture.url}
      headingLevel={4}
      tone={failed ? 'default' : 'flat'}
      aside={<span className={statusClass(capture.status)}>{capture.status}</span>}
    >
      {failed ? <p className={own.captureFailure}>{capture.readFailureKo}</p> : null}

      <dl className={own.captureFacts}>
        {capture.finalUrl === capture.url ? null : (
          <Fact term="최종 주소" detail={capture.finalUrl} />
        )}
        <Fact term="받은 크기" detail={`${formatCount(capture.byteSize)}바이트`} />
        <Fact
          term="받은 때"
          detail={new Date(capture.fetchedAt).toLocaleString('ko-KR')}
        />
        <Fact term="내용 지문" detail={capture.contentHash} />
      </dl>

      <Headers label="우리가 보낸 헤더" headers={capture.requestHeaders} />
      <Headers label="받은 헤더" headers={capture.headers} />

      <details className={own.captureBody}>
        <summary>받은 본문{capture.truncated ? ' (앞부분만)' : ''}</summary>
        {/*
          **글자로만 넣는다.** 남의 사이트에서 받아 온 것이라 HTML 로 그리면 그 안의
          스크립트가 우리 콘솔에서 돈다. React 가 기본으로 이스케이프한다.
        */}
        <pre className={own.captureText}>{capture.body}</pre>
        {capture.truncated ? (
          <p className={own.captureCut}>
            상한을 넘어 앞부분만 남겼습니다. 판정도 이 범위에서 이뤄졌습니다.
          </p>
        ) : null}
      </details>
    </Card>
  );
}

function Fact({ term, detail }: { readonly term: string; readonly detail: string }) {
  return (
    <div className={own.captureFact}>
      <dt>{term}</dt>
      <dd>{detail}</dd>
    </div>
  );
}

function Headers({
  label,
  headers,
}: {
  readonly label: string;
  readonly headers: Readonly<Record<string, string>>;
}) {
  const entries = Object.entries(headers);
  if (entries.length === 0) return null;

  return (
    <details className={own.captureHeaders}>
      <summary>
        {label} ({formatCount(entries.length)})
      </summary>
      <dl className={own.captureFacts}>
        {entries.map(([key, value]) => (
          <Fact key={key} term={key} detail={value} />
        ))}
      </dl>
    </details>
  );
}

/** 2xx 는 조용히, 나머지는 눈에 띄게. 색만으로 말하지 않으므로 숫자는 그대로 보인다. */
function statusClass(status: number): string {
  // CSS 모듈은 이름이 없을 수도 있는 것으로 읽힌다. 빈 문자열이면 색만 없고 숫자는
  // 그대로 보인다 — 색이 사라져도 사실은 안 사라진다.
  if (status >= 200 && status < 300) return own.statusOk ?? '';
  return (status >= 500 ? own.statusFail : own.statusWarn) ?? '';
}
