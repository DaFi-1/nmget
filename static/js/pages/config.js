App.register("config", {
  init(el) {
    const $ = (id) => el.querySelector(`#${id}`);
    const form = $("form-import");
    const file = $("import-file");
    const btnImport = $("btn-import");
    const msg = $("import-msg");
    const zone = $("drop-zone");
    const dropText = $("drop-text");
    const dropName = $("drop-name");

    const setFile = (f) => {
      if (!f) return;
      dropName.textContent = f.name;
      dropName.hidden = false;
      dropText.textContent = "File ready to import";
      zone.classList.add("ready");
    };

    file.addEventListener("change", () => setFile(file.files[0]));

    ["dragover", "dragenter"].forEach((ev) => zone.addEventListener(ev, (e) => {
      e.preventDefault();
      zone.classList.add("dragover");
    }));
    ["dragleave", "drop"].forEach((ev) => zone.addEventListener(ev, (e) => {
      e.preventDefault();
      zone.classList.remove("dragover");
    }));
    zone.addEventListener("drop", (e) => {
      const f = e.dataTransfer.files[0];
      if (f) {
        file.files = e.dataTransfer.files;
        setFile(f);
      }
    });

    form.addEventListener("submit", (e) => {
      e.preventDefault();
      if (!file.files.length) {
        msg.textContent = "Select a file.";
        msg.style.color = "#ef4444";
        return;
      }
      const data = new FormData();
      data.append("file", file.files[0]);
      btnImport.disabled = true;
      msg.textContent = "Importing...";
      msg.style.color = "var(--text-dim)";
      fetch(form.getAttribute("action"), {
        method: "POST",
        body: data
      }).then((r) => r.json()).then((d) => {
        btnImport.disabled = false;
        if (d.ok) {
          msg.textContent = "Database imported.";
          msg.style.color = "var(--green)";
          file.value = "";
          dropName.hidden = true;
          dropText.textContent = "Click to choose or drop the file here";
          zone.classList.remove("ready");
        } else {
          msg.textContent = d.error || "Error.";
          msg.style.color = "#ef4444";
        }
      }).catch(() => {
        btnImport.disabled = false;
        msg.textContent = "Error.";
        msg.style.color = "#ef4444";
      });
    });
  }
});
