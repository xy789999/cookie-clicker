/* Cookie Clicker <-> 本地 Python 工具 桥接脚本
 * 作用：把实时状态（饼干数 / 每秒产量 / 天堂碎片 / 糖果块）上报给本地工具，
 *       并接收“设置饼干数 / 天堂碎片 / 糖果块 / 召唤黄金饼干”指令。
 * 本地工具监听 http://127.0.0.1:8089 （GET /command 取指令，POST /report 推状态）。
 * 工具未运行时这里静默失败，不影响游戏。
 */
(function () {
 // 自动适配桥接地址：页面通过什么 IP 打开，就往同 IP 的 8089 端口发数据
  var TOOL_HOST = (location.hostname && location.hostname !== "") ? location.hostname : "127.0.0.1";
  var TOOL = "http://" + TOOL_HOST + ":8089";
  
  function gameReady() {
    return (typeof Game !== "undefined" && Game && Game.ready && Game.cookiesPs !== undefined);
  }

  function report() {
    if (!gameReady()) return;
    try {
      var data = JSON.stringify({
        cookies: Game.cookies,
        cps: Game.cookiesPs,
        heavenly: Game.heavenlyChips,
        lumps: (typeof Game.lumps !== "undefined" ? Game.lumps : -1)
      });
      fetch(TOOL + "/report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: data
      }).catch(function () {});
    } catch (e) {}
  }

  function poll() {
    if (!gameReady()) return;
    fetch(TOOL + "/command")
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (j && j.set !== null && j.set !== undefined && !isNaN(j.set)) {
          Game.cookies = j.set;
          if (j.set > Game.cookiesEarned) Game.cookiesEarned = j.set;
        }
        if (j && j.setHeavenly !== null && j.setHeavenly !== undefined && !isNaN(j.setHeavenly)) {
          Game.heavenlyChips = j.setHeavenly;
        }
        if (j && j.setLumps !== null && j.setLumps !== undefined && !isNaN(j.setLumps)) {
          try {
            Game.lumps = j.setLumps;
            if (j.setLumps > Game.lumpsTotal) Game.lumpsTotal = j.setLumps;
            if (typeof Game.computeLumpType === "function") Game.computeLumpType();
          } catch (e) {}
        }
        if (j && j.spawnGolden) {
          try {
            if (typeof Game.shimmer === "function") new Game.shimmer("golden");
          } catch (e) {}
        }
      })
      .catch(function () {});
  }

  function boot() {
    var tries = 0;
    var t = setInterval(function () {
      tries++;
      if (gameReady()) {
        clearInterval(t);
        report();
        setInterval(report, 300);
        setInterval(poll, 350);
      } else if (tries > 200) {
        clearInterval(t); // 超过 ~60s 仍未就绪则放弃
      }
    }, 300);
  }

  if (document.readyState === "complete" || document.readyState === "interactive") {
    boot();
  } else {
    window.addEventListener("load", boot);
  }
})();
