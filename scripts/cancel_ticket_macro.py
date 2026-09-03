from __future__ import annotations

import argparse
import os
import time

from ktx_booking import (
    AdultPassenger,
    KorailError,
    NoResultsError,
    PatchedKorail,
    ReserveOption,
    TRAIN_TYPE_MAP,
    normalize_reservation,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="취소표를 반복 조회해 좌석이 생기면 예약합니다.")
    parser.add_argument("dep", help="출발역")
    parser.add_argument("arr", help="도착역")
    parser.add_argument("date", help="출발일 YYYYMMDD")
    parser.add_argument("time", help="희망 시작 시각 HHMMSS")
    parser.add_argument("--interval", type=int, default=5, help="조회 간격(초), 기본 5")
    parser.add_argument("--max-attempts", type=int, default=0, help="최대 조회 횟수, 0이면 Ctrl+C까지 반복")
    parser.add_argument("--train-type", choices=sorted(TRAIN_TYPE_MAP), default="ktx")
    parser.add_argument("--confirm", action="store_true", help="자동 예약을 명시적으로 승인")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.confirm:
        raise SystemExit("자동 예약을 시작하려면 --confirm을 추가하세요.")
    if args.interval < 2:
        raise SystemExit("--interval은 2초 이상이어야 합니다.")
    if args.max_attempts < 0:
        raise SystemExit("--max-attempts는 0 이상이어야 합니다.")

    korail_id = os.environ.get("KSKILL_KTX_ID")
    korail_password = os.environ.get("KSKILL_KTX_PASSWORD")
    if not korail_id or not korail_password:
        raise SystemExit("KSKILL_KTX_ID와 KSKILL_KTX_PASSWORD 환경변수가 필요합니다.")

    passengers = [AdultPassenger()]
    client = PatchedKorail(korail_id, korail_password, auto_login=False)
    attempt = 0
    print(f"취소표 조회 시작: {args.dep} -> {args.arr}, {args.date} {args.time}")
    print(f"조회 간격: {args.interval}초 | 중지: Ctrl+C")

    while args.max_attempts == 0 or attempt < args.max_attempts:
        attempt += 1
        try:
            if not client.logined:
                client.login(korail_id, korail_password)
            if not client.logined:
                print(f"[{attempt}] 로그인 실패. {args.interval}초 후 재시도합니다.")
                time.sleep(args.interval)
                continue
            trains = client.search_train(
                args.dep,
                args.arr,
                args.date,
                args.time,
                train_type=TRAIN_TYPE_MAP[args.train_type],
                passengers=passengers,
            )
            selected_train = trains[0]
            print(f"[{attempt}] 좌석 발견: {selected_train}")
            reservation = client.reserve(
                selected_train,
                passengers=passengers,
                option=ReserveOption.GENERAL_FIRST,
            )
            print("예약 성공")
            print(normalize_reservation(reservation))
            return 0
        except NoResultsError:
            print(f"[{attempt}] 좌석 없음. {args.interval}초 후 재조회합니다.")
        except KorailError as exc:
            print(f"[{attempt}] 코레일 오류: {exc}. {args.interval}초 후 재시도합니다.")
        except KeyboardInterrupt:
            print("\n매크로를 중지했습니다.")
            return 130
        except Exception as exc:
            print(f"[{attempt}] 일시적 오류({type(exc).__name__}). {args.interval}초 후 재시도합니다.")
        time.sleep(args.interval)

    print("최대 조회 횟수에 도달했습니다.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
