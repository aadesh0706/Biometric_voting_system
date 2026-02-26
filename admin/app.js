const API_BASE = "http://localhost:8000";
let token = null;

const loginBtn = document.getElementById("login-btn");
const loadRegsBtn = document.getElementById("load-registrations");
const loadVotesBtn = document.getElementById("load-votes");
const loginStatus = document.getElementById("login-status");
const regEl = document.getElementById("registrations");
const voteEl = document.getElementById("votes");

loginBtn.addEventListener("click", async () => {
  const username = document.getElementById("username").value;
  const password = document.getElementById("password").value;

  const form = new FormData();
  form.append("username", username);
  form.append("password", password);

  try {
    const res = await fetch(`${API_BASE}/admin/login`, { method: "POST", body: form });
    const json = await res.json();
    if (!res.ok) {
      loginStatus.textContent = json.detail || "Login failed";
      return;
    }
    token = json.token;
    loginStatus.textContent = "Logged in";
    document.getElementById("data-card").style.display = "block";
  } catch (err) {
    loginStatus.textContent = "Network error";
  }
});

loadRegsBtn.addEventListener("click", async () => {
  const res = await fetch(`${API_BASE}/admin/registrations`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const json = await res.json();
  regEl.textContent = JSON.stringify(json.registrations, null, 2);
});

loadVotesBtn.addEventListener("click", async () => {
  const res = await fetch(`${API_BASE}/admin/votes`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const json = await res.json();
  voteEl.textContent = JSON.stringify(json.votes, null, 2);
});
