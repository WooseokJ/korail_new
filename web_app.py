from __future__ import annotations

from datetime import date
import os
import threading

from flask import Flask, jsonify, render_template, request

from scripts.ktx_booking import (
    AdultPassenger,
    KorailError,
    NoResultsError,
    PatchedKorail,
    ReserveOption,
    TRAIN_TYPE_MAP,
    find_train_by_id,
    normalize_reservation,
    normalize_train,
)

app = Flask(__name__)
KORAIL_PASSWORD_RESET_URL = "https://www.korail.com/"
macro_lock = threading.Lock()
macro_stop = threading.Event()
macro_state = {"running": False, "attempts": 0, "message": "대기 중", "reservation": None}


@app.route("/", methods=["GET", "POST"])
def index():
    global macro_state
    form = {
        "dep": request.form.get("dep", "서울"),
        "arr": request.form.get("arr", "부산"),
        "date": request.form.get("date", date.today().strftime("%Y%m%d")),
        "time": request.form.get("time", "090000"),
        "train_type": request.form.get("train_type", "ktx"),
        "passenger_count": request.form.get("passenger_count", "1"),
    }
    trains = []
    error = None

    if request.method == "POST":
        macro_stop.set()
        with macro_lock:
            macro_state = {"running": False, "attempts": 0, "message": "새 열차 조회를 준비 중입니다.", "reservation": None}
        korail_id = request.form.get("korail_id", "").strip()
        korail_password = request.form.get("korail_password", "")
        if not korail_id or not korail_password:
            error = "코레일 ID와 비밀번호를 입력해 주세요."
        else:
            try:
                client = PatchedKorail(korail_id, korail_password)
                if not client.logined:
                    error = client.login_message or "코레일 로그인이 거부되었습니다. ID와 비밀번호를 확인해 주세요."
                else:
                    passenger_count = int(form["passenger_count"])
                    if not 1 <= passenger_count <= 9:
                        raise ValueError("예약 매수는 1~9명으로 입력해 주세요.")
                    found = client.search_train_allday(
                        form["dep"],
                        form["arr"],
                        form["date"],
                        form["time"],
                        train_type=TRAIN_TYPE_MAP[form["train_type"]],
                        passengers=[AdultPassenger(passenger_count)],
                        include_no_seats=True,
                    )
                    trains = [normalize_train(train, index) for index, train in enumerate(found, 1)]
            except NoResultsError:
                error = "조건에 맞는 열차가 없습니다. 날짜나 시간을 바꿔 보세요."
            except ValueError as exc:
                error = str(exc)
            except KorailError as exc:
                error = str(exc) or "코레일 요청을 처리하지 못했습니다."
            except Exception as exc:
                app.logger.exception("Korail search failed")
                error = f"요청 중 오류가 발생했습니다: {type(exc).__name__}"

    needs_password_reset = bool(error and ("비밀번호 5회" in error or "로그인 제한" in error))
    return render_template("index.html", form=form, trains=trains, error=error, needs_password_reset=needs_password_reset)
    
@app.post("/reserve")
def reserve():
    field_names = ("dep", "arr", "date", "time", "train_type", "train_id", "passenger_count")
    fields = {name: request.form.get(name, "").strip() for name in field_names}
    korail_id = request.form.get("korail_id", "").strip()
    korail_password = request.form.get("korail_password", "")
    reservation = None
    error = None

    try:
        client = PatchedKorail(korail_id, korail_password)
        if not client.logined:
            raise KorailError(client.login_message or "코레일 로그인이 거부되었습니다. ID와 비밀번호를 확인해 주세요.")
        passenger_count = int(fields["passenger_count"])
        if not 1 <= passenger_count <= 9:
            raise ValueError("예약 매수는 1~9명으로 입력해 주세요.")
        trains = client.search_train(
            fields["dep"], fields["arr"], fields["date"], fields["time"],
            train_type=TRAIN_TYPE_MAP[fields["train_type"]],
            passengers=[AdultPassenger(passenger_count)],
        )
        selected_train = find_train_by_id(trains, fields["train_id"])
        if selected_train is None:
            raise KorailError("열차 정보가 변경되었습니다. 다시 조회해 주세요.")
        reservation = normalize_reservation(
            client.reserve(selected_train, passengers=[AdultPassenger(passenger_count)], option=ReserveOption.GENERAL_FIRST)
        )
    except ValueError as exc:
        error = str(exc)
    except KorailError as exc:
        error = str(exc) or "예약 요청을 처리하지 못했습니다."
    except Exception as exc:
        app.logger.exception("Korail reservation failed")
        error = f"예약 중 오류가 발생했습니다: {type(exc).__name__}"

    form = {name: fields[name] for name in ("dep", "arr", "date", "time", "train_type", "passenger_count")}
    needs_password_reset = bool(error and ("비밀번호 5회" in error or "로그인 제한" in error))
    return render_template("index.html", form=form, trains=[], error=error, reservation=reservation, needs_password_reset=needs_password_reset)


def run_macro(settings: dict[str, str]) -> None:
    try:
        client = PatchedKorail(settings["korail_id"], settings["korail_password"], auto_login=False)
        while not macro_stop.is_set():
            with macro_lock:
                macro_state["attempts"] += 1
                attempt = macro_state["attempts"]
                macro_state["message"] = f"{attempt}회째 좌석을 확인하는 중입니다."
            try:
                if not client.logined:
                    client.login(settings["korail_id"], settings["korail_password"])
                if not client.logined:
                    message = client.login_message or "로그인 실패. 다시 시도하는 중입니다."
                else:
                    passenger_count = int(settings["passenger_count"])
                    trains = client.search_train(
                        settings["dep"], settings["arr"], settings["date"], settings["time"],
                        train_type=TRAIN_TYPE_MAP[settings["train_type"]],
                        passengers=[AdultPassenger(passenger_count)],
                        include_no_seats=True,
                    )
                    selected_train = next(
                        (train for train in trains if normalize_train(train, 0)["train_id"] in settings["train_ids"]),
                        None,
                    )
                    if selected_train is None:
                        message = "선택한 시간대에 좌석 없음. 5초 후 다시 확인합니다."
                    else:
                        reservation = client.reserve(
                            selected_train, passengers=[AdultPassenger(passenger_count)], option=ReserveOption.GENERAL_FIRST
                        )
                        with macro_lock:
                            macro_state["reservation"] = normalize_reservation(reservation)
                            macro_state["message"] = "예약 성공"
                        return
            except NoResultsError:
                message = "좌석 없음. 5초 후 다시 확인합니다."
            except KorailError as exc:
                message = str(exc) or "코레일 오류. 5초 후 다시 확인합니다."
            except Exception as exc:
                app.logger.exception("Web macro failed")
                message = f"일시적 오류({type(exc).__name__}). 5초 후 다시 확인합니다."
            with macro_lock:
                macro_state["message"] = message
            macro_stop.wait(5)
    finally:
        with macro_lock:
            macro_state["running"] = False


@app.post("/macro/start")
def start_macro():
    global macro_state
    with macro_lock:
        if macro_state["running"]:
            return jsonify({"error": "이미 매크로가 실행 중입니다."}), 409
        field_names = ("korail_id", "dep", "arr", "date", "time", "train_type", "passenger_count")
        settings = {name: request.form.get(name, "").strip() for name in field_names}
        settings["train_ids"] = request.form.getlist("train_id")
        settings["korail_password"] = request.form.get("korail_password", "")
        if not all(settings[name] for name in field_names) or not settings["train_ids"]:
            return jsonify({"error": "로그인 정보와 여정 정보를 모두 입력해 주세요."}), 400
        macro_stop.clear()
        macro_state = {"running": True, "attempts": 0, "message": "매크로를 시작합니다.", "reservation": None}
        threading.Thread(target=run_macro, args=(settings,), daemon=True).start()
        return jsonify(macro_state)


@app.post("/macro/stop")
def stop_macro():
    macro_stop.set()
    with macro_lock:
        macro_state["message"] = "중지 요청을 처리하는 중입니다."
    return jsonify(macro_state)


@app.get("/macro/status")
def macro_status():
    with macro_lock:
        return jsonify(macro_state)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("KTX_WEB_PORT", "5001")), debug=False)
