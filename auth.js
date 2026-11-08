const AUTH_TOKEN_KEY = "slai_token";
const AUTH_USER_KEY = "slai_user";
const REMEMBERED_EMAIL_KEY = "slai_remembered_email";

/* Токен и пользователь */

function getToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY) || "";
}

function getAuthHeaders() {
  const token = getToken();

  return token
    ? { "Authorization": "Bearer " + token }
    : {};
}

function setAuth(token, user) {
  if (token) {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
  }

  if (user) {
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
  }

  updateAuthUI();
}

function clearAuth() {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_USER_KEY);
  updateAuthUI();
}

function getCurrentUser() {
  try {
    return JSON.parse(localStorage.getItem(AUTH_USER_KEY) || "null");
  } catch {
    return null;
  }
}

/* Запоминание email */

function rememberEmail(email) {
  if (email) {
    localStorage.setItem(REMEMBERED_EMAIL_KEY, email);
  }
}

function getRememberedEmail() {
  return localStorage.getItem(REMEMBERED_EMAIL_KEY) || "";
}

/* Интерфейс */

function showAuthStatus(text, type = "") {
  const element = document.getElementById("authStatus");

  if (!element) {
    return;
  }

  element.innerText = text;
  element.className = "status " + type;
}

function updateAuthUI() {
  const token = getToken();
  const user = getCurrentUser();

  const authForm = document.getElementById("authForm");
  const authInfo = document.getElementById("authInfo");
  const authBadge = document.getElementById("authBadge");
  const authUserRole = document.getElementById("authUserRole");
  const authUserEmail = document.getElementById("authUserEmail");

  if (token && user) {
    authForm?.classList.add("hidden");
    authInfo?.classList.remove("hidden");
    authBadge?.classList.remove("hidden");

    if (authUserRole) {
      authUserRole.innerText = user.role || "user";
    }

    if (authUserEmail) {
      authUserEmail.innerText = user.email || "";
    }
  } else {
    authForm?.classList.remove("hidden");
    authInfo?.classList.add("hidden");
    authBadge?.classList.add("hidden");

    if (authUserRole) {
      authUserRole.innerText = "";
    }

    if (authUserEmail) {
      authUserEmail.innerText = "";
    }
  }
}

/* Запросы */

async function authRequest(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json; charset=utf-8"
    },
    body: JSON.stringify(payload)
  });

  const text = await response.text();

  let data = {};

  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    throw new Error("Сервер вернул некорректный ответ");
  }

  if (!response.ok) {
    throw new Error(
      data.error ||
      data.message ||
      data.detail ||
      `Ошибка авторизации: HTTP ${response.status}`
    );
  }

  return data;
}

function extractToken(data) {
  return (
    data.token ||
    data.access_token ||
    data.jwt ||
    data.auth_token ||
    data.data?.token ||
    data.data?.access_token ||
    ""
  );
}

function extractUser(data) {
  return (
    data.user ||
    data.profile ||
    data.data?.user || {
      email: data.email || "",
      role: data.role || ""
    }
  );
}

/* Вход */

async function login() {
  const email = document.getElementById("authEmail")?.value.trim();
  const password = document.getElementById("authPassword")?.value;

  if (!email || !password) {
    showAuthStatus("Введите email и пароль", "error");
    return;
  }

  try {
    showAuthStatus("Вход...");

    const data = await authRequest("/api/auth/login", {
      email,
      password
    });

    const token = extractToken(data);

    if (!token) {
      throw new Error("Сервер не вернул токен");
    }

    rememberEmail(email);
    setAuth(token, extractUser(data));

    showAuthStatus("Вход выполнен", "success");
    location.reload();
  } catch (error) {
    showAuthStatus(error.message, "error");
  }
}

/* Регистрация */

async function register() {
  const email = document.getElementById("authEmail")?.value.trim();
  const password = document.getElementById("authPassword")?.value;
  const role = document.getElementById("authRole")?.value || "viewer";

  if (!email || !password) {
    showAuthStatus("Введите email и пароль", "error");
    return;
  }

  try {
    showAuthStatus("Создание аккаунта...");

    const data = await authRequest("/api/auth/register", {
      email,
      password,
      role
    });

    const token = extractToken(data);

    rememberEmail(email);

    if (token) {
      setAuth(token, extractUser(data));
      showAuthStatus("Аккаунт создан", "success");
      location.reload();
      return;
    }

    showAuthStatus("Аккаунт создан. Теперь нажмите «Войти».", "success");
  } catch (error) {
    showAuthStatus(error.message, "error");
  }
}

/* Выход */

function logout() {
  clearAuth();
  location.reload();
}

/* Предпросмотр пароля */

function initPasswordToggle() {
  const passwordInput = document.getElementById("authPassword");
  const toggleButton = document.getElementById("togglePassword");

  if (!passwordInput || !toggleButton) {
    return;
  }

  toggleButton.addEventListener("click", () => {
    const isHidden = passwordInput.type === "password";

    passwordInput.type = isHidden ? "text" : "password";
    toggleButton.innerText = isHidden ? "Скрыть" : "Показать";
    toggleButton.setAttribute(
      "aria-label",
      isHidden ? "Скрыть пароль" : "Показать пароль"
    );
  });
}

/* Подключение обработчиков */

function bindClick(id, handler) {
  const element = document.getElementById(id);

  if (element) {
    element.addEventListener("click", handler);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  bindClick("authLogin", login);
  bindClick("authRegister", register);
  bindClick("authLogout", logout);

  const emailInput = document.getElementById("authEmail");
  const rememberedEmail = getRememberedEmail();

  if (emailInput && rememberedEmail) {
    emailInput.value = rememberedEmail;
  }

  initPasswordToggle();
  updateAuthUI();
});