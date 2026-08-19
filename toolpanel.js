/* Cookie Clicker 网页内置工具面板
 * 直接运行在游戏页面 JS 上下文里，可实时查看并修改：
 *   饼干数 / 每秒产量 / 天堂碎片 / 糖果块，并一键召唤黄金饼干。
 * 默认隐藏，需在“检查 Mon 数据”下方输入兑换码验证通过后才显示。
 * 兑换码在源码中以 SHA-256 哈希存储，不保存明文。
 */
(function () {
  "use strict";

  // ===== 兑换码（SHA-256 哈希，明文不直接出现在源码）=====
  var EXPECTED_CODE_HASH = "50409fcf359184d7b71e1c5fcb45c0cf7be0b2daca7224cc0f2bd07ebcc9c46e";

  // ===== 数字格式化 =====
  function fmt(n) {
    if (!isFinite(n)) return String(n);
    var abs = Math.abs(n);
    if (abs >= 1e15) return n.toExponential(3);
    return Math.floor(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }

  function gameReady() {
    return (typeof Game !== "undefined" && Game && Game.ready && Game.cookiesPs !== undefined);
  }

  // ===== 紧凑 SHA-256（纯 JS，不依赖 Web Crypto）=====
  function sha256(ascii) {
    function rightRotate(value, amount) {
      return (value >>> amount) | (value << (32 - amount));
    }
    var mathPow = Math.pow;
    var maxWord = mathPow(2, 32);
    var lengthProperty = "length";
    var i, j;
    var result = "";
    var words = [];
    var asciiBitLength = ascii[lengthProperty] * 8;
    var hash = sha256.h = sha256.h || [];
    var k = sha256.k = sha256.k || [];
    var primeCounter = k[lengthProperty];
    var isComposite = {};
    for (var candidate = 2; primeCounter < 64; candidate++) {
      if (!isComposite[candidate]) {
        for (i = 0; i < 313; i += candidate) isComposite[i] = candidate;
        hash[primeCounter] = (mathPow(candidate, 0.5) * maxWord) | 0;
        k[primeCounter++] = (mathPow(candidate, 1 / 3) * maxWord) | 0;
      }
    }
    ascii += "\x80";
    while (ascii[lengthProperty] % 64 - 56) ascii += "\x00";
    for (i = 0; i < ascii[lengthProperty]; i++) {
      j = ascii.charCodeAt(i);
      if (j >> 8) return "";
      words[i >> 2] |= j << ((3 - i) % 4) * 8;
    }
    words[words[lengthProperty]] = ((asciiBitLength / maxWord) | 0);
    words[words[lengthProperty]] = (asciiBitLength);
    for (j = 0; j < words[lengthProperty];) {
      var w = words.slice(j, j += 16);
      var oldHash = hash;
      hash = hash.slice(0, 8);
      for (i = 0; i < 64; i++) {
        var w15 = w[i - 15], w2 = w[i - 2];
        var a = hash[0], e = hash[4];
        var temp1 = hash[7] +
          (rightRotate(e, 6) ^ rightRotate(e, 11) ^ rightRotate(e, 25)) +
          ((e & hash[5]) ^ (~e & hash[6])) +
          k[i] +
          (w[i] = (i < 16) ? w[i] :
            (w[i - 16] +
              (rightRotate(w15, 7) ^ rightRotate(w15, 18) ^ (w15 >>> 3)) +
              w[i - 7] +
              (rightRotate(w2, 17) ^ rightRotate(w2, 19) ^ (w2 >>> 10))) | 0);
        var temp2 = (rightRotate(a, 2) ^ rightRotate(a, 13) ^ rightRotate(a, 22)) +
          ((a & hash[1]) ^ (a & hash[2]) ^ (hash[1] & hash[2]));
        hash = [(temp1 + temp2) | 0, hash[0], hash[1], hash[2], (hash[3] + temp1) | 0, hash[4], hash[5], hash[6]];
      }
      for (i = 0; i < 8; i++) hash[i] = (hash[i] + oldHash[i]) | 0;
    }
    for (i = 0; i < 8; i++) {
      for (j = 3; j >= 0; j--) {
        var b = (hash[i] >> (j * 8)) & 255;
        result += ((b >> 4).toString(16)) + ((b & 0x0f).toString(16));
      }
    }
    return result;
  }

  function boot() {
    if (!document.body) { setTimeout(boot, 50); return; }

    // ===== 创建工具面板（初始隐藏）=====
    var panel = document.createElement("div");
    panel.id = "ccToolPanel";
    panel.style.cssText = [
      "position:fixed", "right:10px", "top:10px", "z-index:99999",
      "width:300px", "max-height:94vh", "overflow-y:auto",
      "display:none", // 验证通过前隐藏
      "background:rgba(20,18,30,0.94)", "color:#eee",
      "border:1px solid #5a4b8a", "border-radius:10px",
      "box-shadow:0 4px 18px rgba(0,0,0,0.5)",
      "font-family:'Microsoft YaHei',sans-serif", "font-size:13px",
      "user-select:none"
    ].join(";") + ";";

    panel.innerHTML = [
      '<div id="ccToolHead" style="cursor:move;padding:8px 10px;font-weight:bold;',
      'background:linear-gradient(90deg,#3a2f5e,#5a4b8a);border-radius:9px 9px 0 0;',
      'display:flex;justify-content:space-between;align-items:center;">',
      '<span>🍪 CC 内置工具</span>',
      '<span id="ccToolToggle" style="cursor:pointer;padding:0 6px;">▁</span></div>',
      '<div id="ccToolBody" style="padding:10px;">',

      '<div style="margin-bottom:8px;">',
      '  <div style="color:#9aa;">当前饼干数</div>',
      '  <div id="ccCookies" style="font-size:22px;font-weight:bold;color:#4ea1ff;font-family:Consolas,monospace;">0</div>',
      '  <div id="ccCps" style="color:#9aa;font-size:12px;">每秒产量：0</div>',
      '</div>',
      '<div style="margin-bottom:10px;">',
      '  <div style="color:#9aa;">天堂碎片 (Heavenly Chips)</div>',
      '  <div id="ccHeaven" style="font-size:20px;font-weight:bold;color:#e0a800;font-family:Consolas,monospace;">0</div>',
      '</div>',
      '<div style="margin-bottom:10px;">',
      '  <div style="color:#9aa;">糖果块 (Sugar Lumps)</div>',
      '  <div id="ccLumps" style="font-size:20px;font-weight:bold;color:#ff7fb0;font-family:Consolas,monospace;">0</div>',
      '</div>',

      '<div style="border-top:1px solid #443a66;padding-top:8px;margin-bottom:6px;">',
      '  <div style="margin-bottom:4px;">设为饼干数</div>',
      '  <div style="display:flex;gap:4px;">',
      '    <input id="ccCookieIn" type="text" value="1000000" style="flex:1;min-width:0;padding:4px;',
      '      border-radius:5px;border:1px solid #5a4b8a;background:#15131f;color:#eee;font-family:Consolas,monospace;">',
      '    <button data-set="cookies" style="padding:4px 8px;border:none;border-radius:5px;background:#2e7d32;color:#fff;cursor:pointer;">设置</button>',
      '  </div>',
      '  <div id="ccCookieQ" style="display:flex;flex-wrap:wrap;gap:4px;margin-top:5px;"></div>',
      '</div>',

      '<div style="border-top:1px solid #443a66;padding-top:8px;margin-bottom:6px;">',
      '  <div style="margin-bottom:4px;">设为天堂碎片</div>',
      '  <div style="display:flex;gap:4px;">',
      '    <input id="ccHeavenIn" type="text" value="100" style="flex:1;min-width:0;padding:4px;',
      '      border-radius:5px;border:1px solid #5a4b8a;background:#15131f;color:#eee;font-family:Consolas,monospace;">',
      '    <button data-set="heaven" style="padding:4px 8px;border:none;border-radius:5px;background:#2e7d32;color:#fff;cursor:pointer;">设置</button>',
      '  </div>',
      '  <div id="ccHeavenQ" style="display:flex;flex-wrap:wrap;gap:4px;margin-top:5px;"></div>',
      '</div>',

      '<div style="border-top:1px solid #443a66;padding-top:8px;margin-bottom:6px;">',
      '  <div style="margin-bottom:4px;">设为糖果块</div>',
      '  <div style="display:flex;gap:4px;">',
      '    <input id="ccLumpIn" type="text" value="10" style="flex:1;min-width:0;padding:4px;',
      '      border-radius:5px;border:1px solid #5a4b8a;background:#15131f;color:#eee;font-family:Consolas,monospace;">',
      '    <button data-set="lumps" style="padding:4px 8px;border:none;border-radius:5px;background:#2e7d32;color:#fff;cursor:pointer;">设置</button>',
      '  </div>',
      '  <div id="ccLumpQ" style="display:flex;flex-wrap:wrap;gap:4px;margin-top:5px;"></div>',
      '</div>',

      '<div style="border-top:1px solid #443a66;padding-top:10px;">',
      '  <button id="ccGolden" style="width:100%;padding:8px;border:none;border-radius:6px;',
      '    background:linear-gradient(90deg,#e0a800,#ffcf40);color:#3a2a00;font-weight:bold;',
      '    font-size:14px;cursor:pointer;">✦ 召唤黄金饼干</button>',
      '</div>',

      '</div>'
    ].join("");

    document.body.appendChild(panel);

    // ===== 折叠 =====
    var bodyEl = panel.querySelector("#ccToolBody");
    var toggle = panel.querySelector("#ccToolToggle");
    var collapsed = false;
    toggle.addEventListener("click", function () {
      collapsed = !collapsed;
      bodyEl.style.display = collapsed ? "none" : "block";
      toggle.textContent = collapsed ? "▢" : "▁";
    });

    // ===== 拖动 =====
    var head = panel.querySelector("#ccToolHead");
    var dragging = false, ox = 0, oy = 0;
    head.addEventListener("mousedown", function (e) {
      if (e.target === toggle) return;
      dragging = true;
      var r = panel.getBoundingClientRect();
      ox = e.clientX - r.left;
      oy = e.clientY - r.top;
      e.preventDefault();
    });
    document.addEventListener("mousemove", function (e) {
      if (!dragging) return;
      var x = e.clientX - ox, y = e.clientY - oy;
      x = Math.max(0, Math.min(window.innerWidth - panel.offsetWidth, x));
      y = Math.max(0, Math.min(window.innerHeight - 30, y));
      panel.style.left = x + "px";
      panel.style.top = y + "px";
      panel.style.right = "auto";
    });
    document.addEventListener("mouseup", function () { dragging = false; });

    // ===== 快捷按钮 =====
    function quickRow(containerId, defs) {
      var c = panel.querySelector(containerId);
      defs.forEach(function (d) {
        var b = document.createElement("button");
        b.textContent = d.label;
        b.setAttribute("data-v", d.v);
        b.setAttribute("data-kind", d.kind);
        b.setAttribute("data-target", d.target);
        b.style.cssText = "padding:3px 7px;border:none;border-radius:5px;background:#3a3358;color:#eee;cursor:pointer;font-size:12px;";
        c.appendChild(b);
      });
    }
    quickRow("#ccCookieQ", [
      { label: "+1e3", v: 1e3, kind: "add", target: "cookies" },
      { label: "+1e6", v: 1e6, kind: "add", target: "cookies" },
      { label: "+1e9", v: 1e9, kind: "add", target: "cookies" },
      { label: "×2", v: 2, kind: "mul", target: "cookies" },
      { label: "÷2", v: 0.5, kind: "mul", target: "cookies" },
      { label: "清零", v: 0, kind: "set", target: "cookies" }
    ]);
    quickRow("#ccHeavenQ", [
      { label: "+1", v: 1, kind: "add", target: "heaven" },
      { label: "+10", v: 10, kind: "add", target: "heaven" },
      { label: "+100", v: 100, kind: "add", target: "heaven" },
      { label: "×2", v: 2, kind: "mul", target: "heaven" },
      { label: "÷2", v: 0.5, kind: "mul", target: "heaven" },
      { label: "清零", v: 0, kind: "set", target: "heaven" }
    ]);
    quickRow("#ccLumpQ", [
      { label: "+1", v: 1, kind: "add", target: "lumps" },
      { label: "+10", v: 10, kind: "add", target: "lumps" },
      { label: "+100", v: 100, kind: "add", target: "lumps" },
      { label: "×2", v: 2, kind: "mul", target: "lumps" },
      { label: "÷2", v: 0.5, kind: "mul", target: "lumps" },
      { label: "清零", v: 0, kind: "set", target: "lumps" }
    ]);

    // ===== 操作函数 =====
    function setCookies(v) {
      Game.cookies = v;
      if (v > Game.cookiesEarned) Game.cookiesEarned = v;
    }
    function setHeaven(v) { Game.heavenlyChips = v; }
    function setLumps(v) {
      Game.lumps = v;
      if (v > Game.lumpsTotal) Game.lumpsTotal = v;
      if (typeof Game.computeLumpType === "function") Game.computeLumpType();
    }

    // 设置按钮
    panel.querySelectorAll("button[data-set]").forEach(function (b) {
      b.addEventListener("click", function () {
        var target = b.getAttribute("data-set");
        var inp = panel.querySelector(target === "cookies" ? "#ccCookieIn" : target === "heaven" ? "#ccHeavenIn" : "#ccLumpIn");
        var raw = (inp.value || "").trim().replace(/,/g, "");
        var v = parseFloat(raw);
        if (isNaN(v) || v < 0) { alert("请输入非负数字"); return; }
        if (target === "cookies") setCookies(v);
        else if (target === "heaven") setHeaven(v);
        else setLumps(v);
      });
    });

    // 快捷按钮
    panel.querySelectorAll("#ccCookieQ button, #ccHeavenQ button, #ccLumpQ button").forEach(function (b) {
      b.addEventListener("click", function () {
        var target = b.getAttribute("data-target");
        var kind = b.getAttribute("data-kind");
        var val = parseFloat(b.getAttribute("data-v"));
        var base = target === "cookies" ? Game.cookies : target === "heaven" ? Game.heavenlyChips : Game.lumps;
        var newv;
        if (kind === "add") newv = base + val;
        else if (kind === "mul") newv = base * val;
        else newv = val;
        newv = Math.max(0, newv);
        if (target === "cookies") setCookies(newv);
        else if (target === "heaven") setHeaven(newv);
        else setLumps(newv);
      });
    });

    // 黄金饼干
    panel.querySelector("#ccGolden").addEventListener("click", function () {
      try {
        if (typeof Game.shimmer === "function") new Game.shimmer("golden");
        else if (typeof Game.goldenCookie !== "undefined") Game.goldenCookie.spawn();
      } catch (e) { alert("召唤失败：" + e); }
    });

    // ===== 刷新显示 =====
    function refresh() {
      if (!gameReady()) return;
      panel.querySelector("#ccCookies").textContent = fmt(Game.cookies);
      panel.querySelector("#ccCps").textContent = "每秒产量：" + fmt(Game.cookiesPs);
      panel.querySelector("#ccHeaven").textContent = fmt(Game.heavenlyChips);
      var l = Game.lumps;
      panel.querySelector("#ccLumps").textContent = (l < 0) ? "未解锁（" + l + "）" : fmt(l);
    }

    // ===== 启动刷新循环 =====
    var tries = 0;
    var t = setInterval(function () {
      tries++;
      if (gameReady()) {
        clearInterval(t);
        refresh();
        setInterval(refresh, 300);
      } else if (tries > 200) {
        clearInterval(t);
      }
    }, 300);

    // ===== 兑换码验证 UI =====
    var redeemBox = document.createElement("div");
    redeemBox.id = "ccRedeemBox";
    redeemBox.style.cssText = [
      "margin:8px 0", "padding:10px 12px",
      "background:rgba(10,9,16,0.95)", "color:#eee",
      "border:1px solid #5a4b8a", "border-radius:8px",
      "font-family:'Microsoft YaHei',sans-serif", "font-size:13px",
      "box-shadow:0 2px 10px rgba(0,0,0,0.4)"
    ].join(";") + ";";

    redeemBox.innerHTML = [
      '<div style="font-weight:bold;color:#ffcf40;margin-bottom:6px;">🔑 兑换码验证</div>',
      '<div style="display:flex;gap:6px;">',
      '  <input id="ccRedeemInput" type="text" placeholder="请输入兑换码" autocomplete="off"',
      '    style="flex:1;min-width:0;padding:5px 8px;border-radius:5px;border:1px solid #5a4b8a;',
      '    background:#15131f;color:#eee;font-family:Consolas,monospace;font-size:13px;">',
      '  <button id="ccRedeemBtn" style="padding:5px 12px;border:none;border-radius:5px;',
      '    background:#2e7d32;color:#fff;cursor:pointer;font-weight:bold;">验证</button>',
      '</div>',
      '<div id="ccRedeemMsg" style="margin-top:6px;font-size:12px;min-height:18px;"></div>'
    ].join("");

    var redeemInput = redeemBox.querySelector("#ccRedeemInput");
    var redeemBtn = redeemBox.querySelector("#ccRedeemBtn");
    var redeemMsg = redeemBox.querySelector("#ccRedeemMsg");

    function doVerify() {
      var code = (redeemInput.value || "").trim();
      var hash = sha256(code);
      if (!hash) {
        redeemMsg.textContent = "验证异常，请重试";
        redeemMsg.style.color = "#ff5252";
        return;
      }
      if (hash.toLowerCase() === EXPECTED_CODE_HASH) {
        redeemMsg.textContent = "✓ 验证成功，工具已开启";
        redeemMsg.style.color = "#69f0ae";
        panel.style.display = "block";
        setTimeout(function () {
          redeemBox.style.display = "none";
        }, 1200);
      } else {
        redeemMsg.textContent = "✗ 兑换码错误";
        redeemMsg.style.color = "#ff5252";
      }
    }

    redeemBtn.addEventListener("click", doVerify);
    redeemInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter") doVerify();
    });

    function injectRedeemIntoMenu() {
      var menu = document.getElementById("menu");
      if (!menu) return;

      function tryInsert() {
        // 已在 DOM 中（包括验证成功后被隐藏的）就不再操作，避免重复插入
        if (document.getElementById("ccRedeemBox")) return true;
        var nodes = menu.querySelectorAll("*");
        for (var i = 0; i < nodes.length; i++) {
          var txt = nodes[i].textContent || "";
          // 匹配「检查 Mod 数据」及其大小写变体
          if (/检查\s*Mod\s*数据/i.test(txt)) {
            nodes[i].insertAdjacentElement("afterend", redeemBox);
            return true;
          }
        }
        return false;
      }

      // 首次尝试（菜单可能已存在）
      tryInsert();

      // 游戏会周期性用 innerHTML 重绘 #menu，把我插入的兑换框一并冲掉。
      // 因此观察器【不关闭】：只要兑换框被冲掉（不在 DOM），就重新插回。
      var obs = new MutationObserver(function () {
        if (!document.getElementById("ccRedeemBox")) tryInsert();
      });
      obs.observe(menu, { childList: true, subtree: true });
    }

    injectRedeemIntoMenu();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
