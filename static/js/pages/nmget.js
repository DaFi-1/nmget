App.register("nmget", {
  init(el, state) {
    const $ = (id) => el.querySelector(`#${id}`);
    const form = $("form-nmget");
    const tag = $("tag");
    const duration = $("duration");
    const scriptEl = $("script");
    const btnCopy = $("btn-copy");
    const currentTagName = $("current-tag-name");
    const btnDeleteTag = $("btn-delete-tag");
    const statsBody = $("stats-body");
    const statsTotal = $("stats-total");
    const btnSendAll = $("btn-send-all");
    const btnDeleteAll = $("btn-delete-all");
    const formAddTag = $("form-add-tag");
    const newTag = $("new-tag");
    const addTagMsg = $("add-tag-msg");
    const confirmModal = $("confirm-modal");
    const confirmText = $("confirm-text");
    const btnConfirmYes = $("btn-confirm-yes");
    const btnConfirmNo = $("btn-confirm-no");

    let statsInterval = null;
    let prevStats = "";
    let activated = false;

    const askConfirm = (message, onYes) => {
      confirmText.textContent = message;
      confirmModal.classList.add("show");
      btnConfirmYes.onclick = () => {
        confirmModal.classList.remove("show");
        onYes();
      };
      btnConfirmNo.onclick = () => confirmModal.classList.remove("show");
      confirmModal.onclick = (e) => {
        if (e.target === confirmModal) confirmModal.classList.remove("show");
      };
    };

    const loadTags = () => {
      App.api("/tags")
        .then((d) => {
          const current = tag.value;
          tag.innerHTML = '<option value="" selected>Select the tag</option>';
          d.tags.forEach((t) => {
            const opt = document.createElement("option");
            opt.value = t;
            opt.textContent = t;
            tag.appendChild(opt);
          });
          if (d.tags.includes(current)) tag.value = current;
          update();
        })
        .catch(() => {});
    };

    formAddTag.addEventListener("submit", (e) => {
      e.preventDefault();
      const name = newTag.value.trim();
      if (!name) return;
      App.api("/tags", { method: "POST", body: { name } })
        .then((d) => {
          if (d.ok) {
            newTag.value = "";
            addTagMsg.textContent = `Tag "${d.name}" added.`;
            addTagMsg.style.color = "var(--green)";
            tag.value = d.name;
            loadTags();
          } else {
            addTagMsg.textContent = d.error === "duplicate"
              ? "Tag already exists."
              : (d.error || "Error.");
            addTagMsg.style.color = "#ef4444";
          }
        }).catch(() => {});
    });

    const escapeHtml = (v) => String(v)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");

    const renderStats = (d) => {
      statsBody.innerHTML = "";
      let total = 0;
      d.items.forEach((item) => {
        total += item.quantity;
        const tr = document.createElement("tr");
        tr.innerHTML =
          `<td>${escapeHtml(item.tag)}</td>` +
          `<td class="num" data-value="${escapeHtml(item.quantity)}">0</td>` +
          `<td><div class="row-actions">` +
          `<button class="btn-row btn-row-add" data-tag="${escapeHtml(item.tag)}">Add</button>` +
          `<button class="btn-row btn-row-del" data-tag="${escapeHtml(item.tag)}">Delete</button>` +
          `</div></td>`;
        statsBody.appendChild(tr);
      });
      statsTotal.textContent = total;
      if (d.items.length === 0) {
        const tr = document.createElement("tr");
        tr.innerHTML = '<td class="empty" colspan="3">Empty queue</td>';
        statsBody.appendChild(tr);
      }
      statsBody.querySelectorAll(".num").forEach((node) => {
        const target = parseInt(node.dataset.value, 10);
        let n = 0;
        const step = Math.max(1, Math.ceil(target / 30));
        const timer = setInterval(() => {
          n += step;
          if (n >= target) {
            n = target;
            clearInterval(timer);
          }
          node.textContent = n;
        }, 30);
      });
    };

    const loadStats = () => {
      App.api("/queue")
        .then((d) => {
          const current = JSON.stringify(d.items);
          if (current === prevStats) return;
          prevStats = current;
          renderStats(d);
        })
        .catch(() => {});
    };

    statsBody.addEventListener("click", (e) => {
      const button = e.target.closest(".btn-row");
      if (!button) return;
      const tagName = button.dataset.tag;
      const isAdd = button.classList.contains("btn-row-add");
      const route = isAdd ? "/queue/send" : "/queue/clear";
      askConfirm(
        isAdd
          ? `Move all "${tagName}" numbers to the list?`
          : `Delete all "${tagName}" numbers from the queue?`,
        () => App.api(route, {
          method: "POST",
          body: { tag: tagName }
        }).then(loadStats)
      );
    });

    btnSendAll.addEventListener("click", () => {
      askConfirm("Send all numbers in the queue to the list?", () => {
        App.api("/queue/send", { method: "POST" }).then(loadStats);
      });
    });

    btnDeleteAll.addEventListener("click", () => {
      askConfirm("Delete all numbers from the queue?", () => {
        App.api("/queue/clear", { method: "POST" }).then(loadStats);
      });
    });

    const loadCurrentTag = () => {
      App.api("/tag/current")
        .then((d) => { currentTagName.textContent = d.tag; })
        .catch(() => {});
    };

    btnDeleteTag.addEventListener("click", () => {
      askConfirm("Delete the current tag?", () => {
        App.api("/tag/current", { method: "DELETE" })
          .then((d) => { currentTagName.textContent = d.tag; })
          .catch(() => {});
      });
    });

    const generate = () => {
      const t = tag.value;
      const seg = Math.max(1, parseInt(duration.value, 10) || 10);
      const safeTag = t.replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\n/g, "\\n");
      scriptEl.value = `(() => {
    const REPEAT_INTERVAL = 2000;        // 2 seconds
    const END_TIME = ${seg * 1000}; // ${seg} seconds
    const TAG = "${safeTag}";

    const interval = setInterval(() => {
        const html = document.documentElement.outerHTML;

        const phones = [
            ...html.matchAll(
                /(\\(\\d{2}\\)\\s*\\d{4,5}-\\d{4})/gi
            )
        ].map(m => m[1].replace(/\\D/g, ""));

        if (phones.length > 0) {
            fetch("http://127.0.0.1:5000/phones", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    phones: phones,
                    tag: TAG
                })
            });
        }
    }, REPEAT_INTERVAL);

    setTimeout(() => {
        clearInterval(interval);
    }, END_TIME);
})();`;
    };

    const validate = () => {
      const seg = parseInt(duration.value, 10);
      const filled = tag.value !== "" && Number.isFinite(seg) && seg > 0;
      btnCopy.disabled = !(activated && filled);
    };

    form.addEventListener("submit", (e) => {
      e.preventDefault();
      App.api("/nmget", {
        method: "POST",
        body: { tag: tag.value }
      }).then(() => loadCurrentTag()).catch(() => {});
      activated = true;
      generate();
      validate();
    });

    const update = () => {
      generate();
      validate();
    };

    tag.addEventListener("change", update);
    duration.addEventListener("change", update);

    update();
    loadTags();
    loadCurrentTag();
    loadStats();
    statsInterval = setInterval(loadStats, 2000);

    btnCopy.addEventListener("click", () => {
      if (btnCopy.disabled) return;
      navigator.clipboard.writeText(scriptEl.value);
      btnCopy.textContent = "Copied!";
      setTimeout(() => { btnCopy.textContent = "Copy"; }, 1500);
    });

    state.destroy = () => {
      if (statsInterval) clearInterval(statsInterval);
      statsInterval = null;
    };
  }
});
