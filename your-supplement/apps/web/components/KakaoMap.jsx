'use client';
import { useEffect, useRef } from 'react';

// 카카오맵 SDK를 한 번만 로드 (autoload=false → kakao.maps.load 콜백에서 초기화)
let sdkPromise = null;
function loadKakaoSdk(appKey) {
  if (typeof window === 'undefined') return Promise.reject(new Error('no window'));
  if (window.kakao?.maps) return Promise.resolve(window.kakao);
  if (sdkPromise) return sdkPromise;
  sdkPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = `//dapi.kakao.com/v2/maps/sdk.js?appkey=${appKey}&autoload=false`;
    script.onload = () => window.kakao.maps.load(() => resolve(window.kakao));
    script.onerror = () => reject(new Error('카카오맵 SDK 로드 실패'));
    document.head.appendChild(script);
  });
  return sdkPromise;
}

export default function KakaoMap({ items = [], myLocation, height = 320 }) {
  const ref = useRef(null);
  const appKey = process.env.NEXT_PUBLIC_KAKAO_MAP_KEY;

  useEffect(() => {
    if (!appKey || !ref.current) return;
    let cancelled = false;

    loadKakaoSdk(appKey).then((kakao) => {
      if (cancelled || !ref.current) return;
      const fallback = items.find((it) => it.lat && it.lng);
      const center = myLocation || (fallback ? { lat: fallback.lat, lng: fallback.lng } : { lat: 37.4979, lng: 127.0276 });

      const map = new kakao.maps.Map(ref.current, {
        center: new kakao.maps.LatLng(center.lat, center.lng),
        level: 5,
      });

      // 의료기관 핀
      items.forEach((it) => {
        if (!it.lat || !it.lng) return;
        const marker = new kakao.maps.Marker({ position: new kakao.maps.LatLng(it.lat, it.lng), map });
        const iw = new kakao.maps.InfoWindow({
          content: `<div style="padding:6px 10px;font-size:13px;font-weight:600;">${it.name}</div>`,
        });
        kakao.maps.event.addListener(marker, 'click', () => iw.open(map, marker));
      });

      // 내 위치 (파란 원)
      if (myLocation) {
        new kakao.maps.Circle({
          center: new kakao.maps.LatLng(myLocation.lat, myLocation.lng),
          radius: 30, strokeWeight: 2, strokeColor: '#059669', strokeOpacity: 0.9,
          fillColor: '#059669', fillOpacity: 0.4, map,
        });
      }
    }).catch(() => {});

    return () => { cancelled = true; };
  }, [appKey, items, myLocation]);

  // 키 없으면 안내 플레이스홀더 (화면이 항상 뜨도록)
  if (!appKey) {
    return (
      <div style={{
        height, borderRadius: 'var(--r-xl)', border: '1px dashed var(--hairline)',
        background: 'var(--canvas-soft)', display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', gap: 6, textAlign: 'center', padding: 16,
      }}>
        <span style={{ fontSize: 30 }}>🗺️</span>
        <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink-secondary)' }}>지도를 보려면 카카오맵 키가 필요해요</p>
        <p style={{ fontSize: 12, color: 'var(--ink-faint)' }}>아래 목록은 그대로 사용할 수 있어요 · 키 추가 방법은 SETUP 참고</p>
      </div>
    );
  }

  return <div ref={ref} style={{ height, borderRadius: 'var(--r-xl)', overflow: 'hidden', border: '1px solid var(--hairline)' }} />;
}
