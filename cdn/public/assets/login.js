(function () {
  const send = document.getElementById("send");
  const enter = document.getElementById("enter");
  const code = document.getElementById("code");
  const msg = document.getElementById("msg");

  function setMsg(text) {
    msg.textContent = text || "";
  }

  async function post(path, body) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.ok === false) {
      throw new Error(data.error || "请求失败");
    }
    return data;
  }

  send.addEventListener("click", async () => {
    send.disabled = true;
    setMsg("正在发送…");
    try {
      await post("/api/auth/request");
      setMsg("验证码已发送，请查收邮箱。");
      code.focus();
    } catch (err) {
      setMsg(err.message);
    } finally {
      send.disabled = false;
    }
  });

  async function verify() {
    const value = code.value.replace(/\s+/g, "");
    enter.disabled = true;
    setMsg("正在验证…");
    try {
      await post("/api/auth/verify", { code: value });
      location.href = "/";
    } catch (err) {
      setMsg(err.message);
    } finally {
      enter.disabled = false;
    }
  }

  enter.addEventListener("click", verify);
  code.addEventListener("keydown", (e) => {
    if (e.key === "Enter") verify();
  });
})();
