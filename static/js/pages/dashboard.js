App.register("dashboard", {
  init(el, state) {
    const COR_ON = "#00ff00";
    const COR_OFF = "#4d4d4d";
    const FONT = "TerminessNerdFont-Bold, system-ui, sans-serif";
    const $ = (id) => el.querySelector(`#${id}`);
    const charts = [];
    let interval = null;
    let lastKey = "";

    const setup = () => {
      Chart.defaults.color = "#5f9a5f";
      Chart.defaults.font.family = FONT;
      Chart.defaults.maintainAspectRatio = false;

      charts.push(new Chart($("chart-status"), {
        type: "doughnut",
        data: {
          labels: ["ON (not sent)", "OFF (sent)"],
          datasets: [{ data: [0, 0], backgroundColor: [COR_ON, COR_OFF] }]
        },
        options: {
          cutout: "60%",
          plugins: { legend: { position: "right" } }
        }
      }));

      charts.push(new Chart($("chart-status-tag"), {
        type: "bar",
        data: {
          labels: [],
          datasets: [
            { label: "ON", data: [], backgroundColor: COR_ON },
            { label: "OFF", data: [], backgroundColor: COR_OFF }
          ]
        },
        options: {
          plugins: { legend: { position: "top" } },
          scales: {
            y: { beginAtZero: true, stacked: true, grid: { color: "#032e11" }, ticks: { precision: 0 } },
            x: { stacked: true, grid: { display: false } }
          }
        }
      }));

      charts.push(new Chart($("chart-tag"), {
        type: "bar",
        data: { labels: [], datasets: [{ label: "Numbers", data: [], backgroundColor: "#00ff00" }] },
        options: {
          plugins: { legend: { display: false } },
          scales: {
            y: { beginAtZero: true, grid: { color: "#032e11" }, ticks: { precision: 0 } },
            x: { grid: { display: false } }
          }
        }
      }));

      charts.push(new Chart($("chart-day"), {
        type: "line",
        data: { labels: [], datasets: [{
          label: "Captures",
          data: [],
          borderColor: "#00ff00",
          backgroundColor: "rgba(0, 255, 0, 0.15)",
          fill: true,
          tension: 0.3,
          pointRadius: 2
        }] },
        options: {
          plugins: { legend: { display: false } },
          scales: {
            y: { beginAtZero: true, grid: { color: "#032e11" }, ticks: { precision: 0 } },
            x: { grid: { display: false } }
          }
        }
      }));

      const formatDate = (v) => {
        if (!v) return "—";
        const [date, time] = v.split(" ");
        const [y, m, d] = date.split("-");
        return `${d}/${m}/${y} ${time}`;
      };

      const load = () => {
        App.api("/dashboard/data")
          .then((d) => {
            const key = JSON.stringify(d);
            if (key === lastKey) return;
            lastKey = key;

            $("card-total").textContent = d.total;
            $("card-today").textContent = d.today;
            $("card-tags").textContent = d.by_tag.length;
            $("card-last").textContent = formatDate(d.last_capture);

            const byStatus = new Map(d.by_status.map((s) => [s.status, s.quantity]));
            const on = byStatus.get("ON") || 0;
            const off = byStatus.get("OFF") || 0;
            $("card-on").textContent = on;
            $("card-off").textContent = off;

            charts[0].data.datasets[0].data = [on, off];
            charts[0].update();

            const map = {};
            d.status_by_tag.forEach((x) => {
              if (!map[x.tag]) map[x.tag] = { on: 0, off: 0 };
              if (x.status === "ON") map[x.tag].on += x.quantity;
              else map[x.tag].off += x.quantity;
            });
            charts[1].data.labels = d.by_tag.map((t) => t.tag);
            charts[1].data.datasets[0].data = d.by_tag.map((t) => (map[t.tag] ? map[t.tag].on : 0));
            charts[1].data.datasets[1].data = d.by_tag.map((t) => (map[t.tag] ? map[t.tag].off : 0));
            charts[1].update();

            charts[2].data.labels = d.by_tag.map((t) => t.tag);
            charts[2].data.datasets[0].data = d.by_tag.map((t) => t.quantity);
            charts[2].update();

            charts[3].data.labels = d.by_date.map((x) => x.date);
            charts[3].data.datasets[0].data = d.by_date.map((x) => x.quantity);
            charts[3].update();
          })
          .catch(() => {});
      };

      interval = setInterval(load, 5000);
      load();
    };

    const chartSrc = `/static/vendor/chart.umd.min.js${(window.__VER__ && window.__VER__["vendor/chart.umd.min.js"]) ? `?v=${window.__VER__["vendor/chart.umd.min.js"]}` : ""}`;

    if (window.Chart) {
      setup();
    } else {
      App.loadScript(chartSrc)
        .then(setup)
        .catch(() => {});
    }

    state.destroy = () => {
      if (interval) clearInterval(interval);
      charts.forEach((chart) => chart.destroy());
      charts.length = 0;
    };
  }
});
