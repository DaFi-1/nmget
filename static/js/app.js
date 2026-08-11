(() => {
  "use strict";

  const VERSIONS = window.__VER__ || {};

  const ver = (path) => (VERSIONS[path] ? `?v=${VERSIONS[path]}` : "");

  const App = {
    _modules: new Map(),
    _loaded: new Set(),
    _pending: null,
    _current: null,
  };

  window.App = App;

  App.loadScript = (src) =>
    new Promise((resolve, reject) => {
      const existing = document.querySelector(`script[data-loaded-src="${src}"]`);
      if (existing) {
        if (existing.dataset.ready === "1") resolve();
        else existing.addEventListener("load", resolve);
        return;
      }
      const script = document.createElement("script");
      script.src = src;
      script.dataset.loadedSrc = src;
      script.onload = () => {
        script.dataset.ready = "1";
        resolve();
      };
      script.onerror = () => {
        document.head.removeChild(script);
        reject(new Error(`failed to load ${src}`));
      };
      document.head.appendChild(script);
    });

  App.load = (name) => {
    if (App._loaded.has(name)) return Promise.resolve();
    App._loaded.add(name);
    return App.loadScript(`/static/js/pages/${name}.js${ver(`js/pages/${name}.js`)}`);
  };

  App.api = (url, opts = {}) => {
    if (opts.body !== undefined) {
      opts.headers = Object.assign({ "Content-Type": "application/json" }, opts.headers);
      if (typeof opts.body !== "string") opts.body = JSON.stringify(opts.body);
    }
    return fetch(url, opts).then((r) => r.json());
  };

  App.register = (name, mod) => {
    App._modules.set(name, mod);
    if (App._pending && App._pending.name === name) {
      const pending = App._pending;
      App._pending = null;
      mount(pending.name, pending.el);
    }
  };

  function destroyCurrent() {
    if (App._current && App._current.state.destroy) {
      try {
        App._current.state.destroy();
      } catch (error) {
        console.error("module destroy failed", error);
      }
    }
    App._current = null;
  }

  function mount(name, el) {
    destroyCurrent();
    const state = { destroy: null };
    const mod = App._modules.get(name);
    if (!mod) return;
    if (mod.init) {
      try {
        const result = mod.init(el, state);
        if (typeof result === "function") state.destroy = result;
      } catch (error) {
        console.error("module init failed", error);
      }
    }
    App._current = { name, state };
  }

  function updateChrome(page) {
    const title = page.dataset.pageTitle || "";
    const titleEl = document.getElementById("page-title");
    if (titleEl) titleEl.textContent = title;
    if (title) document.title = `nmGET · ${title}`;
    document.querySelectorAll("#sidebar nav a").forEach((link) => {
      const active = link.dataset.nav === page.dataset.page;
      link.classList.toggle("active", active);
      if (active) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
  }

  function mountFromDom() {
    const appEl = document.getElementById("app");
    const page = appEl && appEl.querySelector("[data-page]");
    if (!page) return;
    appEl.scrollTop = 0;
    updateChrome(page);
    const name = page.dataset.page;
    if (App._modules.has(name)) {
      mount(name, page);
    } else {
      App._pending = { name, el: page };
      App.load(name);
    }
  }

  document.addEventListener("htmx:beforeSwap", () => {
    destroyCurrent();
  });

  document.addEventListener("htmx:afterSwap", () => {
    mountFromDom();
  });

  document.addEventListener("htmx:historyRestore", () => {
    destroyCurrent();
  });

  document.addEventListener("htmx:afterHistoryRestore", () => {
    mountFromDom();
  });

  const progress = document.getElementById("progress");
  let requestCount = 0;
  let progressTimer = null;

  function showProgress() {
    requestCount += 1;
    if (progressTimer) clearTimeout(progressTimer);
    progressTimer = setTimeout(() => progress.classList.add("show"), 150);
  }

  function hideProgress() {
    requestCount = Math.max(0, requestCount - 1);
    if (!requestCount && progressTimer) {
      clearTimeout(progressTimer);
      progressTimer = setTimeout(() => progress.classList.remove("show"), 120);
    }
  }

  document.addEventListener("htmx:beforeRequest", showProgress);
  document.addEventListener("htmx:afterRequest", hideProgress);
  document.addEventListener("htmx:responseError", hideProgress);
  document.addEventListener("htmx:sendError", hideProgress);

  document.addEventListener("pointerover", (event) => {
    const link = event.target.closest("#sidebar nav a[data-nav]");
    if (!link || link.dataset.prefetched) return;
    link.dataset.prefetched = "1";
    const name = link.dataset.nav;
    App.load(name);
    if (name === "dashboard") {
      App.loadScript(`/static/vendor/chart.umd.min.js${ver("vendor/chart.umd.min.js")}`)
        .catch(() => {});
    }
  });

  function startMatrixRain(canvas) {
    if (!canvas) return () => {};
    const reduced =
      window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const ctx = canvas.getContext("2d");
    const parent = canvas.parentElement;
    const chars = "0123456789";
    const fontSize = 14;
    let cols = 0;
    let drops = [];
    let rafId = 0;

    function resize() {
      const dpr = window.devicePixelRatio || 1;
      const width = parent.clientWidth;
      const height = parent.clientHeight;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      cols = Math.max(1, Math.floor(width / fontSize));
      drops = [];
      for (let i = 0; i < cols; i++) {
        drops.push(Math.floor(Math.random() * -40));
      }
    }

    function draw() {
      if (document.hidden || reduced) return;
      ctx.fillStyle = "rgba(0, 0, 0, 0.07)";
      ctx.fillRect(0, 0, parent.clientWidth, parent.clientHeight);
      ctx.font = `${fontSize}px TerminessNerdFontMono-Regular, ui-monospace, monospace`;
      for (let i = 0; i < cols; i++) {
        const x = i * fontSize;
        const y = drops[i] * fontSize;
        ctx.fillStyle = Math.random() > 0.975 ? "#9dff9d" : "#00ff00";
        ctx.fillText(chars[Math.floor(Math.random() * chars.length)], x, y);
        if (y > parent.clientHeight && Math.random() > 0.975) drops[i] = 0;
        drops[i]++;
      }
    }

    resize();
    window.addEventListener("resize", resize);
    const loop = () => {
      draw();
      rafId = requestAnimationFrame(loop);
    };
    if (!reduced) rafId = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(rafId);
      window.removeEventListener("resize", resize);
    };
  }

  startMatrixRain(document.getElementById("matrix-rain"));
  startMatrixRain(document.getElementById("topbar-matrix-rain"));

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mountFromDom);
  } else {
    mountFromDom();
  }
})();
