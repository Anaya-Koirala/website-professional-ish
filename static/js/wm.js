const WM = (() => {
    let zTop = 100;
    let focusedId = null;
    const windows = {}; // id → { el, tbBtn, minimized }
    const maximized = {}; // id → saved styles before maximize
    let spawnX = 0, spawnY = 0;
    const layer = () => document.getElementById("win-layer");
    const tbWins = () => document.getElementById("tb-wins");

    // Map window id to its taskbar/title icon
    const ICONS = {
        home: "/static/icon/home.png",
        messages: "/static/icon/messages.png",
        writings: "/static/icon/writings.png",
        courses: "/static/icon/courses.png",
        github: "/static/icon/github.png",
        resume: "/static/icon/resume.png",
        contact: "/static/icon/contact.png",
    };

    function iconFor(id) {
        if (id && id.startsWith("course_")) return "/static/icon/folder.png";
        return ICONS[id] || "";
    }

    // Bring window to front and mark it active in the title bar + taskbar
    function focusWin(id) {
        if (focusedId && windows[focusedId]) {
            windows[focusedId].el.querySelector(".title-bar").classList.remove("active");
            windows[focusedId].tbBtn.classList.remove("focused");
        }
        focusedId = id;
        if (!windows[id]) return;
        windows[id].el.style.zIndex = ++zTop;
        windows[id].el.querySelector(".title-bar").classList.add("active");
        windows[id].tbBtn.classList.add("focused");
    }

    // Drag a window by its title bar, clamped to the desktop area
    function makeDraggable(win, titleBar) {
        let ox, oy, dragging = false;
        titleBar.addEventListener("mousedown", e => {
            if (e.target.closest(".title-bar-controls")) return;
            dragging = true;
            ox = e.clientX - win.offsetLeft;
            oy = e.clientY - win.offsetTop;
            focusWin(win.dataset.wid);
            e.preventDefault();
        });
        document.addEventListener("mousemove", e => {
            if (!dragging) return;
            win.style.left = Math.max(0, Math.min(e.clientX - ox, window.innerWidth - win.offsetWidth)) + "px";
            win.style.top = Math.max(0, Math.min(e.clientY - oy, window.innerHeight - 28 - win.offsetHeight)) + "px";
        });
        document.addEventListener("mouseup", () => {
            dragging = false;
        });
    }

    // Build and return the window DOM element
    function buildWin(id, title, bodyHTML, width, height) {
        const x = Math.round((window.innerWidth - width) / 2) + (spawnX % 5) * 20;
        const y = Math.round((window.innerHeight - 28 - height) / 2) + (spawnY % 5) * 5;
        spawnX++;
        spawnY++;
        const icon = iconFor(id);
        const win = document.createElement("div");
        win.className = "w98-win window";
        win.dataset.wid = id;
        win.style.cssText = `left:${x}px;top:${y}px;width:${width}px;height:${height}px;z-index:${++zTop};`;
        win.innerHTML = `
      <div class="title-bar">
        <div class="title-bar-text">
          ${icon ? `<img src="${icon}" style="width:14px;height:14px;image-rendering:pixelated;vertical-align:middle;margin-right:4px;">` : ""}
          ${title}
        </div>
        <div class="title-bar-controls">
          <button aria-label="Minimize" data-action="min"></button>
          <button aria-label="Maximize" data-action="max"></button>
          <button aria-label="Close"    data-action="close"></button>
        </div>
      </div>
      <div class="window-body">${bodyHTML}</div>`;
        win.querySelector("[data-action=close]").addEventListener("click", () => closeWin(id));
        win.querySelector("[data-action=min]").addEventListener("click", () => minimizeWin(id));
        win.querySelector("[data-action=max]").addEventListener("click", () => maximizeWin(id));
        win.addEventListener("mousedown", () => focusWin(id));
        makeDraggable(win, win.querySelector(".title-bar"));
        return win;
    }

    // Build the taskbar button; clicking it toggles minimize or focuses
    function buildTbBtn(id, title) {
        const icon = iconFor(id);
        const btn = document.createElement("button");
        btn.className = "tb-btn button";
        btn.dataset.wid = id;
        btn.innerHTML = `${icon ? `<img src="${icon}">` : ""}<span>${title}</span>`;
        btn.addEventListener("click", () => {
            const w = windows[id];
            if (!w) return;
            if (w.minimized) {
                w.el.style.display = "";
                w.minimized = false;
                focusWin(id);
            } else if (focusedId === id) {
                minimizeWin(id);
            } else {
                focusWin(id);
            }
        });
        return btn;
    }

    function registerWin(id, title, el) {
        const tbBtn = buildTbBtn(id, title);
        tbWins().appendChild(tbBtn);
        windows[id] = {
            el, tbBtn, minimized: false
        };
        layer().appendChild(el);
        focusWin(id);
    }

    function closeWin(id) {
        if (!windows[id]) return;
        windows[id].el.remove();
        windows[id].tbBtn.remove();
        delete windows[id];
        focusedId = null;
        // Focus the most recently opened remaining window
        const ids = Object.keys(windows);
        if (ids.length) focusWin(ids[ids.length - 1]);
    }

    function minimizeWin(id) {
        if (!windows[id]) return;
        windows[id].el.style.display = "none";
        windows[id].minimized = true;
        windows[id].tbBtn.classList.remove("focused");
        focusedId = null;
    }

    function maximizeWin(id) {
        if (!windows[id]) return;
        const el = windows[id].el;
        if (maximized[id]) {
            // Restore saved dimensions
            Object.assign(el.style, maximized[id]);
            delete maximized[id];
        } else {
            maximized[id] = {
                left: el.style.left, top: el.style.top, width: el.style.width, height: el.style.height
            };
            Object.assign(el.style, {
                left: "0", top: "0", width: "100vw", height: "calc(100vh - 28px)"
            });
        }
        focusWin(id);
    }

    // --- Public API ---

    // Open a Flask route in an iframe window. Re-opening focuses the existing window.
    // id is also used as the title and the URL slug (e.g. "home" → "/home")
    function open(id, width = 800, height = 640) {
        openURL(`/${id}`, id, width, height);
    }

    function openURL(url, id, width = 800, height = 640) {
        if (windows[id]) {
            if (windows[id].minimized) {
                windows[id].el.style.display = "";
                windows[id].minimized = false;
            }
            focusWin(id);
            return;
        }

        const title = url === `/${id}` ? id.charAt(0).toUpperCase() + id.slice(1) : id.toUpperCase();

        const body = `<iframe src="${url}" style="width:100%;height:100%;border:none;display:block;" title="${title}"></iframe>`;
        const win = buildWin(id, title, body, width, height);

        win.querySelector(".window-body").style.cssText = "flex:1;overflow:hidden;padding:0;background:#fff;";

        registerWin(id, title, win);
    }

    // Open a window with raw HTML content (no iframe)
    function dialog(id, htmlString, width=360, height=240) {
        if (windows[id]) {
            focusWin(id);
            return;
        }
        const title = id.charAt(0).toUpperCase() + id.slice(1);
        const win = buildWin(id, title, htmlString, width, height);
        registerWin(id, title, win);
    }

    // Open an external link in a new tab
    function openExternal(url) {
        window.open(url, "_blank", "noopener,noreferrer");
    }

    // Return an HTML string that embeds a PDF from /static/docs/<filename>.pdf
    function embedPDF(filename, src) {
        return `<object data="${src}" type="application/pdf" style="width:100%;height:100%;border:none;">
      <p style="padding:12px;">PDF not supported. <a href="${src}" download>Download ${filename}.pdf</a></p>
    </object>`;
    }

    // Start the taskbar clock
    document.addEventListener("DOMContentLoaded", () => {
        const clock = document.getElementById("tb-clock");
        const tick = () => {
            clock.textContent = new Date().toLocaleTimeString("en-US", {
                hour: "2-digit", minute: "2-digit", hour12: true
            });
        };
        tick();
        setInterval(tick, 60000);
    });

    // add to return statement:
    return {
        open, openURL, dialog, openExternal, embedPDF
    };
})();