<img width="1536" height="551" alt="image" src="https://github.com/user-attachments/assets/001e3a59-547e-48d3-be9b-b8cf4d83913d" />


**Number Map Get** — capture and organize phone numbers from **Google Maps** to build contact lists.

![License](https://img.shields.io/badge/license-GPL--3.0-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab.svg)
![Flask](https://img.shields.io/badge/Flask-3.x-000000.svg)
![SQLite](https://img.shields.io/badge/database-SQLite-003b57.svg)

---

## 📸 Screenshots

Project screenshots (one below the other).

<!-- To change the pictures, just replace the src addresses below. -->

<img alt="Dashboard - nmGET" src="https://github.com/user-attachments/assets/2a7d7a89-de65-49ae-923c-bd59447785b4">
<img alt="Script generation - nmGET" src="https://github.com/user-attachments/assets/36b3d14d-f06c-40b5-9610-8e3e4f5ec403">
<img alt="Contact lists - nmGET" src="https://github.com/user-attachments/assets/b577c98b-fb89-42d7-bb97-7eecad0b9218">
<img alt="Settings - nmGET" src="https://github.com/user-attachments/assets/a5078d3e-19ac-4307-b078-46b31d7c1c3b">

---

## 📖 About

**nmGET** stands for **Number Map Get**: the application was originally designed to **extract data
from Google Maps** — such as the phone numbers of businesses displayed on the page. The main way of
using it is still to open Google Maps, paste the generated script into the browser console and capture
the numbers visible on the displayed area.

nmGET generates a **JavaScript script** that collects phone numbers from a web page and sends them to
a server, where they are organized by **tags**. **Future updates intend to generalize** the tool for
other number-scraping pages, beyond Google Maps.

With the captured numbers you can:

- track the capture volume on a **dashboard** with charts;
- manage a **capture queue** per tag;
- generate **clickable contact lists** in the `wa.me` format (WhatsApp), with light or dark theme;
- **export and import** the database.

### Why was it developed?

This project was developed for **study purposes** of web development: Flask, SQLite, vanilla
JavaScript, client-server integration (via JSON API), charts with Chart.js and navigation with htmx.
It is **fully functional and usable**, but it was created in an educational context.

### ⚠️ Disclaimer

> This software is provided **for study and learning purposes only**. The author is **not
> responsible** for any misuse, illegal activity or anything that violates third-party terms of
> service. Use it only on pages you control or for which you have permission.

---

## ✨ Features

- **Capture script generation** — choose the tag and the running time (10s up to 1h) and copy a ready-to-use JS script.
- **Google Maps capture** — paste the script into the browser console on the Google Maps page and it collects the numbers visible on the map. Future updates will generalize it to other pages.
- **Tags** — create, select and delete tags to organize your contacts.
- **Dashboard** — total numbers, captured today, last capture and charts (status, by tag, per day).
- **Capture queue** — pending numbers, with actions to send (moves them into the contacts base) and delete.
- **List generator** — generates an HTML file with clickable `wa.me` links, marks numbers as sent and highlights the ones already accessed.
- **Export/Import** — download or restore the whole database.
- **Technical extras** — open CORS, gzip compression, SQLite in WAL mode, query cache, dark theme and Matrix effect.

## 🛠️ Tech stack

| Layer       | Technology                                    |
|-------------|-----------------------------------------------|
| Backend     | Python 3.10+ with Flask 3.x                   |
| Database    | SQLite (WAL mode, optimized indexes)          |
| Frontend    | Vanilla HTML, CSS and JavaScript              |
| Auxiliary   | htmx (navigation), Chart.js (charts)          |

---

## 🚀 Installation

### Prerequisites

- **Python 3.10 or higher** — check with `python3 --version`.
- **git** — to clone the repository (optional if you download the zip).
- No external database is needed: SQLite is created automatically on the first run.

### Step by step

**1. Clone the repository**

```bash
git clone git@github.com:DaFi-1/nmget.git
cd nmget
```

> If you prefer, use HTTPS: `git clone https://github.com/DaFi-1/nmget.git`

**2. Create a virtual environment**

```bash
python3 -m venv venv
```

**3. Activate the virtual environment**

Linux/macOS:

```bash
source venv/bin/activate
```

Windows (PowerShell):

```powershell
venv\Scripts\Activate.ps1
```

**4. Install the dependencies**

```bash
pip install -r requirements.txt
```

**5. Start the server**

```bash
python main.py
```

You will see the development server URL in the terminal.

**6. Open the application**

Open your browser at: <http://127.0.0.1:5000>

The database (`instance/nmget.db`) is created automatically on the first access.

### Running in production (optional)

For a production server with Gunicorn:

```bash
pip install gunicorn
gunicorn -w 2 -b 127.0.0.1:5000 main:app
```

---

## 📖 How to use

The application has 4 pages accessible from the sidebar (with the Matrix effect in the background).

### 1. Dashboard (home)

Shows the general capture overview:

- **Cards at the top** — total captured numbers, captured today and the date/time of the last capture.
- **"Overall status" chart** — ratio between pending (`ON`) and sent (`OFF`) numbers.
- **"Status by tag" chart** — stacked bars with pending/sent numbers per tag.
- **"Numbers by tag" chart** — total volume of each tag.
- **"Captures per day" chart** — line with the number of captures per day.

The data is refreshed automatically every few seconds.

### 2. Nmget — capturing numbers (main feature)

This is the central screen of the project. The flow is:

**a) Choose or create the tag**

In the **Add tag** section, type the name and click **Add**. The new tag will appear in the list.

**b) Configure the capture**

In the **Configuration** section:

- **Tag** — select the tag that will receive the numbers.
- **Duration** — how long the script should capture (10s, 20s, 60s, 5m, 10m, 30m or 1h).

Click **Activate script**. The **Generated script** field will be filled with a ready-to-use
JavaScript block.

**c) Copy the script**

Click **Copy**. The script goes to your clipboard.

**d) Run it on Google Maps**

Open **Google Maps** (https://maps.google.com) on the page with the businesses you want to capture
and paste the script into the **browser console** (F12 → Console) and press Enter.
Alternatively, you can inject the code into the page itself.

> The script reads the numbers that are **visible on the screen** (in the displayed map area). Scroll
> the map to load more results and repeat the scan within the chosen time.
>
> This is the only scraping page implemented so far. **Future updates will generalize nmGET to other
> number-capturing pages.**

The script will:

1. scan the page for phone numbers (10 to 13 digits);
2. collect the unique numbers and deduplicate them;
3. send them to the server under the chosen tag (via `POST /phones`);
4. repeat the scan every ~2s until the chosen time expires.

> The browser must keep Google Maps **open** during the capture.

**e) Follow the queue**

The **Capture queue** section lists how many numbers are waiting, per tag. Available actions:

- **Send all** — moves all queued numbers into the contacts base (status `ON`, pending).
- **Delete all** — removes the queued numbers.
- Per tag — individual send/delete buttons.

**f) Delete tags**

The **Current tag** section shows the active tag; **Delete tag** removes the current tag
(the default `EMPTY` tag cannot be deleted).

### 3. Ngenerate — generating contact lists

Turns the captured numbers into a clickable WhatsApp list.

1. Select the **tag** and the **quantity** of numbers (max. 5,000).
2. Click **Generate** — the list is built and shown in the **Preview**.
3. Choose the theme (light/dark) and click **Download**.

The downloaded file is a self-contained HTML that:

- lists each number as a `wa.me` link (opens a WhatsApp conversation);
- uses the international format (+55 Brazil);
- **marks as accessed** the links you clicked (crossed out, using local storage) so you don't click them twice.

> When you download a list, the corresponding numbers are marked as **sent** (`OFF`) in the database.

### 4. Config — exporting and importing data

- **Export database** — downloads the full `nmget.db` file (with a WAL checkpoint to guarantee consistency).
- **Import database** — uploads a `.db` file to replace the current one. The database is validated before
  applying, and a backup (`nmget.db.bak`) is kept.

---

## 🔌 API (reference)

| Method | Route                 | Description                                            |
|--------|-----------------------|--------------------------------------------------------|
| GET    | `/`                   | Redirects to `/dashboard`                              |
| GET    | `/dashboard`          | Dashboard page                                         |
| GET    | `/dashboard/data`     | JSON with the statistics                               |
| GET    | `/nmget`              | Capture page (also accepts `POST` to create a tag)     |
| GET    | `/tag/current`        | Active tag                                             |
| DELETE | `/tag/current`        | Deletes the active tag                                 |
| GET    | `/tags`               | Lists the tags                                         |
| POST   | `/tags`               | Creates a tag                                          |
| GET    | `/ngenerate`          | List generator page                                    |
| GET    | `/ngenerate/tags`     | Pending counts per tag                                 |
| POST   | `/ngenerate/generate` | Generates the number list                              |
| POST   | `/ngenerate/download` | Downloads the HTML list and marks as sent              |
| POST   | `/phones`             | Receives captured numbers (CORS enabled)               |
| GET    | `/queue`              | Capture queue per tag                                  |
| POST   | `/queue/send`         | Sends the queue into the contacts base                 |
| POST   | `/queue/clear`        | Clears the queue                                       |
| GET    | `/config`             | Settings page                                          |
| GET    | `/config/export`      | Downloads the database                                 |
| POST   | `/config/import`      | Imports a database                                     |

### Sending numbers example (`/phones`)

```bash
curl -X POST http://127.0.0.1:5000/phones \
  -H "Content-Type: application/json" \
  -d '{"tag": "campaign", "phones": ["83999991111", "83988882222"]}'
```

---

## 📁 Project structure

```
nmget/
├── app/
│   ├── __init__.py        # application factory + gzip middleware
│   ├── db.py              # database layer (SQLite) and models
│   └── views/             # blueprints: dashboard, nmget, ngenerate, phones, queue, config
├── static/
│   ├── css/style.css      # interface styles
│   ├── js/                # app.js and per-page scripts
│   └── vendor/            # local libraries (htmx, chart.js)
├── templates/
│   ├── layouts/base.html  # base layout (sidebar, matrix rain)
│   └── pages/             # dashboard, nmget, ngenerate, config
├── instance/              # SQLite database (created at runtime)
├── main.py                # entry point
├── requirements.txt       # dependencies
└── LICENSE                # GNU GPL v3
```

---

## ⚖️ License

This project is distributed under the **GNU General Public License v3.0**. See the
[LICENSE](LICENSE) file for full details.

Summary: you may use, study, modify and redistribute it, as long as you keep the same license and
disclose your changes. There are no warranties — the software is provided "as is".

---

## ⚠️ Legal notice

**This project was developed for study purposes.** It is functional software, but the author is
**not responsible** for misuse, capturing data without authorization or any violation of terms of
service or legislation. Use it at your own risk and only where permitted.
