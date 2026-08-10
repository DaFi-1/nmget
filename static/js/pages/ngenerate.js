App.register("ngenerate", {
  init(el, state) {
    const $ = (id) => el.querySelector(`#${id}`);
    const form = $("form-config");
    const select = $("cfg-tag");
    const quantity = $("cfg-quantity");
    const theme = $("cfg-theme");
    const info = $("cfg-info");
    const preview = $("preview");
    const btnDownload = $("btn-download");
    const btnGenerate = $("btn-generate");
    const dlForm = $("dl-form");
    const dlPayload = $("dl-payload");
    const dlFrame = $("dl-frame");
    const dlModal = $("dl-modal");
    const dlModalText = $("dl-modal-text");
    const btnDlYes = $("btn-dl-yes");
    const btnDlNo = $("btn-dl-no");

    let generated = { tag: "", numbers: [] };
    let downloading = false;

    const loadTags = () => {
      fetch("/ngenerate/tags")
        .then((r) => r.json())
        .then((d) => {
          const current = select.value;
          select.innerHTML = '<option value="" selected>Select the tag</option>';
          d.items.forEach((item) => {
            const opt = document.createElement("option");
            opt.value = item.tag;
            opt.textContent = `${item.tag} (${item.quantity} available)`;
            select.appendChild(opt);
          });
          if (d.items.some((i) => i.tag === current)) select.value = current;
        })
        .catch(() => {});
    };

    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const tag = select.value;
      const qty = Math.max(1, parseInt(quantity.value, 10) || 10);
      if (!tag) {
        info.textContent = "Select a tag.";
        info.style.color = "#ef4444";
        return;
      }
      btnGenerate.disabled = true;
      info.textContent = "Generating...";
      info.style.color = "var(--text-dim)";
      fetch("/ngenerate/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tag, quantity: qty, dark: theme.value === "black" })
      }).then((r) => r.json()).then((d) => {
        btnGenerate.disabled = false;
        if (!d.ok) {
          info.textContent = d.error || "Error.";
          info.style.color = "#ef4444";
          return;
        }
        preview.srcdoc = d.html;
        generated = { tag: d.tag, numbers: d.numbers };
        downloading = false;
        btnDownload.disabled = d.count === 0;
        if (d.count > 0) {
          info.textContent = `${d.count} numbers from "${d.tag}".`;
          info.style.color = "var(--green)";
        } else {
          info.textContent = `No pending numbers for "${d.tag}".`;
          info.style.color = "#ef4444";
        }
      }).catch(() => {
        btnGenerate.disabled = false;
        info.textContent = "Error.";
        info.style.color = "#ef4444";
      });
    });

    const afterDownload = () => {
      if (!downloading) return;
      downloading = false;
      preview.srcdoc = "";
      btnDownload.disabled = true;
      info.textContent = "Downloaded. Numbers marked as OFF.";
      info.style.color = "var(--green)";
      loadTags();
    };

    const doDownload = () => {
      dlPayload.value = JSON.stringify({
        tag: generated.tag,
        numbers: generated.numbers,
        dark: theme.value === "black"
      });
      dlForm.submit();
      btnDownload.disabled = true;
      downloading = true;
      dlFrame.addEventListener("load", afterDownload, { once: true });
      setTimeout(afterDownload, 1500);
    };

    btnDownload.addEventListener("click", () => {
      if (generated.numbers.length === 0) return;
      dlModalText.textContent =
        `Download ${generated.numbers.length} numbers from "${generated.tag}"?`;
      dlModal.classList.add("show");
    });

    btnDlYes.addEventListener("click", () => {
      dlModal.classList.remove("show");
      doDownload();
    });

    btnDlNo.addEventListener("click", () => {
      dlModal.classList.remove("show");
    });

    dlModal.addEventListener("click", (e) => {
      if (e.target === dlModal) dlModal.classList.remove("show");
    });

    loadTags();

    state.destroy = () => {
      downloading = false;
    };
  }
});
