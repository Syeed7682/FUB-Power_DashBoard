# app.py - FINAL BEMS PROJECT - 100% WORKING (November 23, 2025 Compatible)
from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import plotly.express as px
import plotly.io as pio
import numpy as np
import os

app = Flask(__name__)
DATA_FILE = "data/energy_data.csv"
STATUS_FILE = "data/device_status.csv"
os.makedirs("data", exist_ok=True)


# === GENERATE REALISTIC DATA (ONLY IF FILES MISSING) ===
def generate_unique_data():
    rooms = [
        "FUB-101", "FUB-102", "FUB-103", "FUB-201", "FUB-202", "FUB-203",
        "FUB-301", "FUB-302", "FUB-303", "FUB-401", "FUB-402", "FUB-403",
        "FUB-501", "FUB-502", "FUB-503", "FUB-601", "FUB-602", "FUB-603",
        "FUB-701", "FUB-702", "FUB-703", "FUB-801", "FUB-802", "FUB-803",
        "FUB-901", "FUB-902", "FUB-903", "FUB-1001", "FUB-1002", "FUB-1003"
    ]
    # Generate data for TODAY: 2025-11-23 (or current date)
    dates = pd.date_range("2025-11-23 00:00", "2025-11-23 23:59", freq="T")
    np.random.seed(42)

    data_list = []
    for idx, room in enumerate(rooms):
        voltage = 220 + np.random.normal(0, 3 + idx * 0.5, len(dates))
        hour = dates.hour
        weekday = dates.dayofweek
        base_on = (hour >= 8) & (hour < 20) & (weekday < 5)
        usage_factor = max(0.1, 0.6 + (idx * 0.08))
        random_off = np.random.rand(len(dates)) < (1 - usage_factor)
        is_on = base_on & (~random_off)
        base_current = 4.5 + idx * 0.7 + np.random.normal(0, 0.6, len(dates))
        current = np.where(is_on, base_current, 0.0)
        power = voltage * current

        df = pd.DataFrame({
            "timestamp": dates,
            "room": room,
            "voltage": np.round(voltage, 2),
            "current": np.round(current, 2),
            "power": np.round(power, 1),
            "energy_kwh": np.round(power / 1000 / 60, 6)
        })
        df["bill_taka"] = np.round(df["energy_kwh"] * 5.5, 2)
        df["carbon_gco2"] = np.round(df["energy_kwh"] * 720, 1)
        data_list.append(df)

    full = pd.concat(data_list, ignore_index=True)
    full.to_csv(DATA_FILE, index=False)

    status = pd.DataFrame({
        "room": rooms,
        "status": ["On"] * len(rooms),
        "schedule_on": ["08:00"] * len(rooms),
        "schedule_off": ["20:00"] * len(rooms)
    })
    status.to_csv(STATUS_FILE, index=False)


# Generate only if files don't exist
if not os.path.exists(DATA_FILE) or not os.path.exists(STATUS_FILE):
    generate_unique_data()

# Building floors
floors = {
    "Floor 1":  ["FUB-101", "FUB-102", "FUB-103"],
    "Floor 2":  ["FUB-201", "FUB-202", "FUB-203"],
    "Floor 3":  ["FUB-301", "FUB-302", "FUB-303"],
    "Floor 4":  ["FUB-401", "FUB-402", "FUB-403"],
    "Floor 5":  ["FUB-501", "FUB-502", "FUB-503"],
    "Floor 6":  ["FUB-601", "FUB-602", "FUB-603"],
    "Floor 7":  ["FUB-701", "FUB-702", "FUB-703"],
    "Floor 8":  ["FUB-801", "FUB-802", "FUB-803"],
    "Floor 9":  ["FUB-901", "FUB-902", "FUB-903"],
    "Floor 10": ["FUB-1001", "FUB-1002", "FUB-1003"]
}


@app.route("/")
def index():
    data = pd.read_csv(DATA_FILE)
    data["timestamp"] = pd.to_datetime(data["timestamp"])
    status = pd.read_csv(STATUS_FILE)
    status_dict = dict(zip(status["room"], status["status"]))

    return render_template("index.html",
                           floors=floors,
                           status_dict=status_dict,
                           total_energy=round(data["energy_kwh"].sum(), 2),
                           total_bill=int(round(data["bill_taka"].sum())),
                           total_carbon=int(round(data["carbon_gco2"].sum())))


@app.route("/room/<room_id>", methods=["GET", "POST"])
def room(room_id):
    # Always read latest data
    data = pd.read_csv(DATA_FILE)
    data["timestamp"] = pd.to_datetime(data["timestamp"])
    status_df = pd.read_csv(STATUS_FILE)

    room_row = status_df[status_df["room"] == room_id]
    if room_row.empty:
        return "Room not found", 404
    room_status = room_row.iloc[0].to_dict()

    if request.method == "POST":
        action = request.form.get("action")
        if not action:
            if "toggle" in request.form: action = "toggle"
            elif "schedule" in request.form: action = "schedule"

        if action == "toggle":
            current = status_df.loc[status_df["room"] == room_id, "status"].values[0]
            status_df.loc[status_df["room"] == room_id, "status"] = "Off" if current == "On" else "On"

        elif action == "schedule":
            on_time = request.form.get("on_time", "08:00")
            off_time = request.form.get("off_time", "20:00")
            status_df.loc[status_df["room"] == room_id, ["schedule_on", "schedule_off"]] = [on_time, off_time]

        status_df.to_csv(STATUS_FILE, index=False)
        return redirect(url_for("room", room_id=room_id))

    # AUTO DETECT CORRECT DATE RANGE FROM YOUR CSV
    min_date = data["timestamp"].dt.date.min().isoformat()
    max_date = data["timestamp"].dt.date.max().isoformat()

    start = request.args.get("start", min_date)
    end = request.args.get("end", max_date)

    try:
        start_dt = pd.to_datetime(start).date()
        end_dt = pd.to_datetime(end).date()
    except:
        start_dt = data["timestamp"].dt.date.min()
        end_dt = data["timestamp"].dt.date.max()

    mask = (data["room"] == room_id) & \
           (data["timestamp"].dt.date >= start_dt) & \
           (data["timestamp"].dt.date <= end_dt)
    df = data[mask].copy()

    if df.empty:
        return f'''
        <div style="padding:50px; text-align:center; font-family:Arial;">
            <h2>No Data for {room_id}</h2>
            <p>Your data exists only on: <strong>{min_date}</strong></p>
            <a href="/room/{room_id}?start={min_date}&end={min_date}" 
               class="btn btn-success btn-lg">Load Today's Data (2025-11-23)</a>
            <br><br><a href="/">Back to Home</a>
        </div>
        '''

    # Latest reading
    on_df = df[df["current"] > 0.5]
    latest = on_df.iloc[-1] if not on_df.empty else df.iloc[-1]

    # Hourly charts
    hourly = df.set_index("timestamp")[["voltage", "current", "power"]].resample("H").mean().reset_index()
    if hourly.empty:
        hourly = pd.DataFrame({"timestamp": [df["timestamp"].iloc[0]], "voltage": [220], "current": [0], "power": [0]})

    colors = ["#9b59b6", "#8e44ad", "#6c5ce7"]
    figs = {}
    for i, col in enumerate(["voltage", "current", "power"]):
        fig = px.line(hourly, x="timestamp", y=col, title=f"{col.capitalize()} (Hourly)",
                      color_discrete_sequence=[colors[i]])
        fig.update_layout(template="plotly_white", height=320, margin=dict(l=20,r=20,t=40,b=20))
        figs[col] = pio.to_html(fig, full_html=False)

    total_kwh = df["energy_kwh"].sum()
    savings = total_kwh * 0.20

    return render_template("room.html",
                           room_id=room_id,
                           voltage_html=figs["voltage"],
                           current_html=figs["current"],
                           power_html=figs["power"],
                           total_kwh=round(total_kwh, 3),
                           total_bill=int(round(df["bill_taka"].sum())),
                           total_carbon=int(round(df["carbon_gco2"].sum())),
                           savings_kwh=round(savings, 3),
                           savings_tk=int(round(savings * 5.5)),
                           current_v=round(latest["voltage"], 1),
                           current_i=round(latest["current"], 1),
                           current_p=int(round(latest["power"])),
                           status=room_status.get("status", "Off"),
                           sched_on=room_status.get("schedule_on", "08:00"),
                           sched_off=room_status.get("schedule_off", "20:00"),
                           start=start, end=end)


@app.route("/floor/<floor_name>")
def floor(floor_name):
    if floor_name not in floors:
        return "Floor not found", 404

    data = pd.read_csv(DATA_FILE)
    data["timestamp"] = pd.to_datetime(data["timestamp"])
    rooms_list = floors[floor_name]
    floor_data = data[data["room"].isin(rooms_list)]
    status_df = pd.read_csv(STATUS_FILE)
    status_dict = dict(zip(status_df["room"], status_df["status"]))

    total_energy = floor_data["energy_kwh"].sum()
    total_bill = floor_data["bill_taka"].sum()
    total_carbon = floor_data["carbon_gco2"].sum()

    avg = floor_data.groupby("room")["power"].mean().reset_index()
    if avg.empty:
        avg = pd.DataFrame({"room": rooms_list, "power": [0]*len(rooms_list)})

    fig = px.bar(avg, x="room", y="power", color="power", color_continuous_scale="Viridis",
                 title=f"Average Power - {floor_name}")
    fig.update_layout(template="plotly_white")
    power_chart = pio.to_html(fig, full_html=False)

    room_info = []
    for room in rooms_list:
        room_df = floor_data[floor_data["room"] == room]
        latest = room_df.iloc[-1] if not room_df.empty else {"current": 0, "power": 0}
        room_info.append({
            "id": room,
            "status": status_dict.get(room, "Off"),
            "current": round(latest.get("current", 0), 1),
            "power": int(round(latest.get("power", 0)))
        })

    return render_template("floor.html",
                           floor_name=floor_name,
                           total_energy=round(total_energy, 2),
                           total_bill=int(round(total_bill)),
                           total_carbon=int(round(total_carbon)),
                           power_chart=power_chart,
                           rooms=room_info)


@app.route("/admin", methods=["GET", "POST"])
def admin():
    status_df = pd.read_csv(STATUS_FILE)
    if request.method == "POST":
        action = request.form.get("action") or ("add" if "add" in request.form else "delete" if "delete" in request.form else "toggle")
        if action == "add":
            room = request.form.get("new_room", "").strip()
            if room and room not in status_df["room"].values:
                new = pd.DataFrame({"room": [room], "status": ["On"], "schedule_on": ["08:00"], "schedule_off": ["20:00"]})
                status_df = pd.concat([status_df, new], ignore_index=True)
                status_df.to_csv(STATUS_FILE, index=False)
        elif action == "delete" and request.form.get("room"):
            status_df = status_df[status_df["room"] != request.form.get("room")]
            status_df.to_csv(STATUS_FILE, index=False)
        elif action == "toggle" and request.form.get("room"):
            room = request.form.get("room")
            current = status_df.loc[status_df["room"] == room, "status"].values[0]
            status_df.loc[status_df["room"] == room, "status"] = "Off" if current == "On" else "On"
            status_df.to_csv(STATUS_FILE, index=False)

    status_df = pd.read_csv(STATUS_FILE)
    return render_template("admin.html", rooms=status_df.to_dict("records"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)