// 기본 알림 대신 이 폼의 말풍선만 표시합니다. 서버 검증은 그대로 유지합니다.
const entryForm = document.getElementById("entry-form");

if (entryForm) {
  const fields = [entryForm.elements.namedItem("name"), entryForm.elements.namedItem("message")];

  function isValid(field) {
    return field.value.trim().length > 0 && field.validity.valid;
  }

  function showError(field, visible) {
    const bubble = document.getElementById(`${field.id}-error`);
    bubble.hidden = !visible;
    if (visible) {
      field.setAttribute("aria-invalid", "true");
      field.setAttribute("aria-describedby", `${field.id}-help ${bubble.id}`);
    } else {
      field.removeAttribute("aria-invalid");
      field.setAttribute("aria-describedby", `${field.id}-help`);
    }
  }

  fields.forEach((field) => {
    field.addEventListener("input", () => {
      if (isValid(field)) showError(field, false);
    });
  });

  entryForm.addEventListener("submit", (event) => {
    const firstInvalid = fields.find((field) => !isValid(field));
    fields.forEach((field) => showError(field, field === firstInvalid));
    if (firstInvalid) {
      event.preventDefault();
      firstInvalid.focus();
    }
  });

  // 스크립트 로드에 실패하면 HTML의 required 기본 검증이 계속 동작합니다.
  entryForm.noValidate = true;
}
