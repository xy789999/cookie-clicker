/*
 * langpatch.js — 让 Cookie Clicker 在任意环境（含内置预览沙箱 / file://）都能正常切换并保留语言。
 *
 * 原游戏的语言切换逻辑（Game.showLangSelection）：
 *   点语言 -> localStorageSet('CookieClickerLang', lang) -> Game.toReload=true -> 下一帧 location.reload()
 *   刷新后 window.onload 读 localStorageGet('CookieClickerLang') 加载对应语言包。
 *
 * 断点：在 opaque-origin 沙箱（部分内置预览面板）里，刷新后 localStorage/cookie 均读不到，
 *       于是回退到 EN，语言“切不过去/一刷新就还原”。
 *
 * 修复策略：
 *   1) 存储兜底 shim：localStorageGet/Set 写入失败时回退到 内存 + Cookie（真实可用环境不受影响）。
 *   2) 选择语言时把所选语言写入 URL hash（#lang=FR）——hash 在 location.reload() 后必然保留，
 *      彻底绕开 localStorage 持久化问题。启动时 localStorageGet 优先读 hash。
 *   3) 主路径：写入 hash 后 location.reload()，由原有 window.onload 逻辑加载正确语言（全量切换，最可靠）。
 *   4) 兜底路径：若沙箱拦截 location.reload()，则原地加载语言包并重新本地化界面（菜单/建筑/升级），即时生效。
 */
(function () {
  var mem = {};
  function cookieGet(k) {
    try {
      var m = document.cookie.match('(^|; )' + k + '=([^;]*)');
      return m ? decodeURIComponent(m[1]) : null;
    } catch (e) { return null; }
  }
  function cookieSet(k, v) {
    try { document.cookie = k + '=' + encodeURIComponent(v) + ';path=/;max-age=31536000'; } catch (e) {}
  }

  function getHashLang() {
    try {
      var m = String(window.location.hash || '').match(/[#&]lang=([A-Za-z0-9\-]+)/);
      return m ? m[1] : null;
    } catch (e) { return null; }
  }
  function setHashLang(l) {
    try { window.location.hash = 'lang=' + l; } catch (e) {}
  }

  var _get = localStorageGet;
  var _set = localStorageSet;

  localStorageGet = function (key) {
    // 语言优先从 URL hash 读取（刷新后仍在）
    if (key === 'CookieClickerLang') {
      var h = getHashLang();
      if (h) return h;
    }
    try {
      var v = _get(key);
      if (v !== 0 && v !== null && v !== undefined && v !== '') return v;
    } catch (e) {}
    if (Object.prototype.hasOwnProperty.call(mem, key)) return mem[key];
    var c = cookieGet(key);
    if (c !== null) return c;
    return 0;
  };

  localStorageSet = function (key, str) {
    try { _set(key, str); } catch (e) {}
    try { mem[key] = str; } catch (e) {}
    try { if (typeof str === 'string' && str.length < 2000) cookieSet(key, str); } catch (e) {}
    return str;
  };

  // 原地切换语言（刷新被沙箱拦截时的兜底，或用于即时反馈）
  function applyLangInPlace(lang) {
    try {
      if (typeof LoadLang !== 'function' || typeof Game === 'undefined' || !Game) return;
      LoadLang('loc/' + lang + '.js?v=' + (Game.version || ''), function () {
        try {
          // 重新本地化建筑 / 升级显示名
          if (Game.Objects) {
            for (var i in Game.Objects) {
              try { if (Game.Objects[i].name) Game.Objects[i].dname = loc(Game.Objects[i].name); } catch (e) {}
            }
          }
          if (Game.Upgrades) {
            for (var u in Game.Upgrades) {
              try { if (!Game.Upgrades[u].dname && Game.Upgrades[u].name && Game.Upgrades[u].name !== '???') Game.Upgrades[u].dname = loc(Game.Upgrades[u].name); } catch (e) {}
            }
          }
          try { Game.UpdateMenu(); } catch (e) {}
          try { Game.BuildStore(); } catch (e) {}
          try { Game.RebuildUpgrades(); } catch (e) {}
          try { if (Game.tooltip) Game.tooltip.hide(); } catch (e) {}
        } catch (e) {}
      });
    } catch (e) {}
  }

  window.addEventListener('load', function () {
    if (typeof Game === 'undefined' || !Game) return;
    var _show = Game.showLangSelection;
    Game.showLangSelection = function (firstLaunch) {
      try { if (_show) _show(firstLaunch); } catch (e) {}
      setTimeout(function () {
        var LangsRef = (typeof Langs !== 'undefined') ? Langs : (window.Langs || {});
        for (var i in LangsRef) {
          (function (lang) {
            var el = document.getElementById('langSelect-' + i);
            if (el && !el._lpPatched) {
              el._lpPatched = 1;
              el.addEventListener('click', function () {
                try {
                  localStorageSet('CookieClickerLang', lang); // 最佳努力持久化
                  setHashLang(lang);                          // 刷新后保留，绕过沙箱存储限制
                  try { if (Game.ClosePrompt) Game.ClosePrompt(); } catch (e) {}
                  applyLangInPlace(lang);                     // 即时反馈（刷新被拦截时也生效）
                  setTimeout(function () {
                    try { window.location.reload(); } catch (e) { /* 沙箱拦截刷新：原地切换已生效 */ }
                  }, 30);
                } catch (e) { applyLangInPlace(lang); }
              });
            }
          })(i);
        }
      }, 80);
    };
  });
})();
