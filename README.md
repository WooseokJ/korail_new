## Vercel 배포

이 프로젝트는 `api/index.py`를 Vercel Python Function 진입점으로 사용합니다.

### Vercel 대시보드

1. GitHub 저장소를 Vercel에 Import합니다.
2. Framework Preset은 `Other`로 두고 Root Directory는 저장소 루트로 둡니다.
3. Deploy를 실행합니다.

### Vercel CLI

```bash
npm i -g vercel
vercel login
vercel
vercel --prod
```

`requirements.txt`에 Flask 및 Korail API 의존성이 선언되어 있으므로 별도 Build Command는 필요하지 않습니다.

Vercel은 요청 단위의 서버리스 실행 환경입니다. 검색과 단건 예약은 요청 안에서 처리되지만, 프로세스 메모리와 백그라운드 스레드를 사용하는 자동 예약 감시 기능은 인스턴스 종료나 재배포 시 중단될 수 있습니다. 자동 감시를 안정적으로 운영하려면 별도의 상시 실행 서버나 작업 큐를 사용해야 합니다.

