const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const DEFAULT_PREVIEW = [
  "把想法落到纸上，字迹不必完全相同。",
  "轻微的起伏、间距和墨色变化，会让每一页更自然。",
  "今天也要认真写字。",
].join("\n");

const PAPER_TEMPLATE_BACKGROUNDS = {
  photo_blank: 'url("/static/assets/desk-reference-local.jpg"), url("/static/assets/papers/previews/reference-blank-desk.jpg")',
  reference_blank_desk: 'url("/static/assets/papers/previews/reference-blank-desk.jpg")',
  reference_blank_warm: 'url("/static/assets/papers/previews/reference-blank-warm.jpg")',
  reference_blank_cool: 'url("/static/assets/papers/previews/reference-blank-cool.jpg")',
  reference_blank_mono: 'url("/static/assets/papers/previews/reference-blank-mono.jpg")',
  reference_lined_photo: 'url("/static/assets/papers/previews/reference-lined-photo.jpg")',
  reference_lined_clean: 'url("/static/assets/papers/previews/reference-lined-clean.jpg")',
  reference_notebook: 'url("/static/assets/papers/previews/reference-notebook.jpg")',
  reference_report_body: 'url("/static/assets/papers/previews/reference-report-body.jpg")',
  reference_report_cover: 'url("/static/assets/papers/previews/reference-report-cover.jpg")',
};

const PAPER_TEMPLATE_LAYOUTS = {
  photo_blank: { margins: [0.12, 0.10, 0.10, 0.08], ratio: 1.334, fontSize: 42, lineHeight: 68 },
  reference_blank_desk: { margins: [0.12, 0.10, 0.10, 0.08], ratio: 1.334, fontSize: 42, lineHeight: 68 },
  reference_blank_warm: { margins: [0.12, 0.10, 0.10, 0.08], ratio: 1.334, fontSize: 42, lineHeight: 68 },
  reference_blank_cool: { margins: [0.12, 0.10, 0.10, 0.08], ratio: 1.334, fontSize: 42, lineHeight: 68 },
  reference_blank_mono: { margins: [0.12, 0.10, 0.10, 0.08], ratio: 1.334, fontSize: 42, lineHeight: 68 },
  reference_lined_photo: { margins: [0.06, 0.04, 0.05, 0.03], ratio: 1.105, fontSize: 41, lineHeight: 59 },
  reference_lined_clean: { margins: [0.105, 0.0825, 0.04, 0.09], ratio: 1.414, fontSize: 40, lineHeight: 84 },
  reference_notebook: { margins: [0.06, 0.06, 0.045, 0.035], ratio: 1.328, fontSize: 37, lineHeight: 68 },
  reference_report_body: { margins: [0.065, 0.04, 0.15, 0.045], ratio: 1.778, fontSize: 46, lineHeight: 76 },
  reference_report_cover: { margins: [0.10, 0.075, 0.57, 0.065], ratio: 1.778, fontSize: 46, lineHeight: 69 },
  grid: { margins: [0.10, 0.10, 0.08, 0.08], ratio: 1.414, fontSize: 40, lineHeight: 68 },
  blank: { margins: [0.10, 0.10, 0.08, 0.08], ratio: 1.414, fontSize: 42, lineHeight: 68 },
};

const PAPER_STYLE_CLASSES = [
  "photo_blank", "reference_blank_desk", "reference_blank_warm", "reference_blank_cool",
  "reference_blank_mono", "custom_photo", "reference_lined_photo", "reference_lined_clean", "reference_notebook",
  "reference_report_body", "reference_report_cover", "lined", "report", "grid", "blank",
];

const state = {
  documentFile: null,
  fontUpload: null,
  paperUrl: "",
  fonts: [],
  fontFaces: new Map(),
  paperStyle: "reference_blank_desk",
  result: null,
  currentPage: 0,
  zoom: 72,
  toastTimer: null,
};

const form = $("#render-form");
const fontSelect = $("#font-id");
const paper = $("#live-paper");
const paperContent = $("#paper-content");
const studio = $("#studio");
const resultImage = $("#result-image");
const loadingOverlay = $("#loading-overlay");
const renderButton = $("#render-button");
const message = $("#message");

const downloadLinks = {
  png: $("#download-png"),
  pdf: $("#download-pdf"),
  zip: $("#download-zip"),
};

function numberValue(selector) {
  return Number($(selector).value);
}

function selectedValue(name, fallback = "") {
  return $(`input[name="${name}"]:checked`)?.value || fallback;
}

function showToast(text, type = "info") {
  window.clearTimeout(state.toastTimer);
  message.textContent = text;
  message.className = `toast ${type}`;
  message.hidden = false;
  state.toastTimer = window.setTimeout(() => {
    message.hidden = true;
  }, 3200);
}

function setServiceState(status, text) {
  $("#health").dataset.state = status;
  $("#health-text").textContent = text;
}

async function apiJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || `请求失败 (${response.status})`);
  }
  return data;
}

function setLoading(active) {
  loadingOverlay.hidden = !active;
  renderButton.disabled = active;
  $("#render-button > span").textContent = active ? "正在生成" : "生成预览";
}

function setLink(link, href, enabled) {
  link.href = enabled ? href : "#";
  link.classList.toggle("disabled", !enabled);
  link.setAttribute("aria-disabled", String(!enabled));
}

function setDownloads(data) {
  const enabled = Boolean(data?.pages?.length);
  setLink(downloadLinks.pdf, data?.pdf_url, enabled);
  setLink(downloadLinks.zip, data?.zip_url, enabled);
  setLink(downloadLinks.png, data?.pages?.[state.currentPage]?.url, enabled);
  $("#header-export").disabled = !enabled;
  $("#export-status").textContent = enabled ? `${data.page_count} 页已就绪` : "等待生成";
}

function revokeObjectUrl(key) {
  if (state[key]) {
    URL.revokeObjectURL(state[key]);
    state[key] = "";
  }
}

function filenameWithoutExtension(name) {
  return name.replace(/\.[^.]+$/, "") || "未命名文稿";
}

function setProjectName(name) {
  $("#project-name").textContent = name || "未命名文稿";
}

function setSaveState(text = "参数已更新 · 等待生成") {
  $("#save-state").textContent = text;
}

function plainTextFromMarkdown(text) {
  return text
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/^\s*[-*+]\s+/gm, "• ")
    .replace(/!\[[^\]]*\]\([^)]*\)/g, "")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/[*_~`>#]/g, "")
    .trim();
}

function updatePaperText(text = DEFAULT_PREVIEW) {
  const content = (text || DEFAULT_PREVIEW).trim().slice(0, 280);
  paperContent.replaceChildren();
  const date = document.createElement("p");
  date.className = "paper-date";
  date.textContent = "2026 / HANDDRAFT";
  paperContent.appendChild(date);
  for (const paragraphText of content.split(/\n+/).filter(Boolean).slice(0, 5)) {
    const paragraph = document.createElement("p");
    paragraph.textContent = paragraphText;
    paperContent.appendChild(paragraph);
  }
}

async function previewDocument(file) {
  const extension = file.name.split(".").pop()?.toLowerCase();
  if (["md", "markdown", "txt"].includes(extension)) {
    const text = await file.text();
    updatePaperText(extension === "txt" ? text : plainTextFromMarkdown(text));
    return;
  }
  updatePaperText(`Word 文档“${filenameWithoutExtension(file.name)}”已准备好。\n生成后可查看完整排版效果。`);
}

function setDocument(file) {
  state.documentFile = file;
  $("#document-name").textContent = file ? file.name : "选择 Markdown 或 Word";
  setProjectName(file ? filenameWithoutExtension(file.name) : "未命名文稿");
  setSaveState(file ? "文档仅在本机处理 · 等待生成" : "本地处理 · 未上传服务器");
  if (file) {
    previewDocument(file).catch(() => updatePaperText());
  } else {
    updatePaperText();
  }
}

function switchInputMode(mode) {
  const directText = $("#direct-text");
  const documentDrop = $("#document-drop");
  const textMode = mode === "text";
  directText.hidden = !textMode;
  documentDrop.hidden = textMode;
  if (textMode) {
    setProjectName("直接输入文稿");
    updatePaperText(directText.value || DEFAULT_PREVIEW);
  } else {
    setProjectName(state.documentFile ? filenameWithoutExtension(state.documentFile.name) : "未命名文稿");
    if (state.documentFile) previewDocument(state.documentFile).catch(() => updatePaperText());
    else updatePaperText();
  }
}

function scaledImageSize(width, height) {
  const scale = Math.min(1, 3200 / width, 4200 / height, Math.sqrt(8000000 / (width * height)));
  return [Math.max(1, Math.floor(width * scale)), Math.max(1, Math.floor(height * scale))];
}

async function imageDimensions(file) {
  const bitmap = await createImageBitmap(file);
  const dimensions = [bitmap.width, bitmap.height];
  bitmap.close();
  return dimensions;
}

function applyTemplateLayout(layout, width = 1240, includeTypography = true) {
  const height = Math.round(width * layout.ratio);
  const [left, right, top, bottom] = layout.margins;
  $("#page-width").value = String(width);
  $("#page-height").value = String(height);
  $("#margin-left").value = String(Math.round(width * left));
  $("#margin-right").value = String(Math.round(width * right));
  $("#margin-top").value = String(Math.round(height * top));
  $("#margin-bottom").value = String(Math.round(height * bottom));
  if (includeTypography) {
    $("#font-size").value = String(layout.fontSize);
    $("#line-height").value = String(layout.lineHeight);
  }
}

async function setCustomBackground(file) {
  revokeObjectUrl("paperUrl");
  if (!file) {
    state.paperStyle = "reference_blank_desk";
    $("#background-name").textContent = "上传一张带纸张与环境的图片";
    applyTemplateLayout(PAPER_TEMPLATE_LAYOUTS[state.paperStyle]);
  } else {
    try {
      const [sourceWidth, sourceHeight] = await imageDimensions(file);
      const [width, height] = scaledImageSize(sourceWidth, sourceHeight);
      state.paperUrl = URL.createObjectURL(file);
      state.paperStyle = "custom_photo";
      $("#background-name").textContent = file.name;
      applyTemplateLayout({ margins: [0.12, 0.10, 0.10, 0.08], ratio: height / width }, width, false);
      $("#use-background-size").checked = true;
    } catch {
      $("#background").value = "";
      $("#background-name").textContent = "无法读取图片，请重新选择";
      showToast("无法读取这张背景图片", "error");
    }
  }
  updatePaperAppearance();
  updateSceneAppearance();
  updateLiveTypography();
  setSaveState();
}

function updatePaperAppearance() {
  paper.classList.remove(...PAPER_STYLE_CLASSES);
  paper.classList.add(state.paperStyle);
  $$(".paper-preset").forEach((button) => {
    button.classList.toggle("active", button.dataset.paper === state.paperStyle);
  });
  studio.dataset.paper = state.paperStyle;
}

function updateSceneAppearance() {
  const mode = selectedValue("scene-mode", "desk_photo");
  const templateBackground = PAPER_TEMPLATE_BACKGROUNDS[state.paperStyle];
  const directBackground = state.paperUrl ? `url("${state.paperUrl}")` : templateBackground;
  const directTemplate = Boolean(directBackground);
  studio.dataset.output = mode;
  studio.classList.toggle("direct-template", directTemplate);
  if (directTemplate) {
    studio.style.backgroundImage = "none";
    studio.style.backgroundColor = "#dfe4e1";
    paper.style.backgroundImage = directBackground;
    paper.style.backgroundPosition = "center";
    paper.style.backgroundRepeat = "no-repeat";
    paper.style.backgroundSize = "cover";
  } else {
    studio.style.removeProperty("background-image");
    studio.style.removeProperty("background-color");
    paper.style.removeProperty("background-image");
    paper.style.removeProperty("background-position");
    paper.style.removeProperty("background-repeat");
    paper.style.removeProperty("background-size");
    paper.style.removeProperty("height");
    paper.style.removeProperty("width");
  }
  $$(".mode-card").forEach((card) => {
    card.classList.toggle("active", $("input", card).checked);
  });
}

function selectedFont() {
  return state.fonts.find((font) => font.id === fontSelect.value) || null;
}

function fontFamily(font) {
  return `HandDraft-${font.id}`;
}

async function ensureFontLoaded(font) {
  if (!font) return null;
  if (!state.fontFaces.has(font.id)) {
    const family = fontFamily(font);
    const face = new FontFace(family, `url("/api/fonts/${font.id}/file")`);
    const promise = face.load().then((loaded) => {
      document.fonts.add(loaded);
      return family;
    });
    state.fontFaces.set(font.id, promise);
  }
  return state.fontFaces.get(font.id);
}

async function updateFontPreview() {
  const font = selectedFont();
  if (!font && state.fontUpload) return;
  try {
    const family = await ensureFontLoaded(font);
    if (!family || fontSelect.value !== font.id) return;
    paper.style.setProperty("--preview-font", `"${family}"`);
    $("#selected-font-sample").style.fontFamily = family;
    $(`.font-card[data-font-id="${font.id}"]`)?.style.setProperty("--card-font", family);
  } catch {
    showToast("字体预览加载失败，生成仍可继续", "error");
  }
}

function renderFontPresets(fonts) {
  const container = $("#font-presets");
  container.replaceChildren();
  for (const font of fonts.filter((item) => item.category === "normal" || item.source === "user").slice(0, 6)) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "font-card";
    button.dataset.fontId = font.id;
    const sourceLabel = font.source === "reference" ? "参考项目字库" : font.source === "open" ? "OFL 开源" : "用户字体";
    button.innerHTML = `<span><strong>认真写字</strong><small>${font.name} · ${sourceLabel}</small></span><em>✓</em>`;
    button.addEventListener("click", () => {
      fontSelect.value = font.id;
      fontSelect.dispatchEvent(new Event("change", { bubbles: true }));
      $("#type-section").scrollIntoView({ behavior: "smooth", block: "center" });
    });
    container.appendChild(button);
    ensureFontLoaded(font).then((family) => {
      button.style.setProperty("--card-font", family);
    }).catch(() => {});
  }
  if (!container.children.length) {
    const empty = document.createElement("p");
    empty.className = "status-line";
    empty.textContent = "暂无正常手写字体，请安装或上传字体。";
    container.appendChild(empty);
  }
}

async function loadFonts(preferredId = "") {
  fontSelect.disabled = true;
  fontSelect.innerHTML = '<option value="">读取字体中</option>';
  try {
    const data = await apiJson("/api/fonts");
    const visible = data.fonts.filter((font) => font.category === "normal" || font.source === "user");
    state.fonts = visible.length ? visible : data.fonts.filter((font) => font.category !== "cursive");
    fontSelect.replaceChildren();
    for (const font of state.fonts) {
      const option = document.createElement("option");
      option.value = font.id;
      const source = font.source === "reference" ? "参考项目字库" : font.source === "open" ? "开源手写" : font.source === "user" ? "用户字体" : "本机字体";
      option.textContent = `${font.name} · ${source}`;
      fontSelect.appendChild(option);
    }
    const nextId = preferredId || data.default_id;
    if (state.fonts.some((font) => font.id === nextId)) fontSelect.value = nextId;
    renderFontPresets(state.fonts);
    updateActiveFont();
    await updateFontPreview();
  } catch (error) {
    fontSelect.innerHTML = '<option value="">字体读取失败</option>';
    showToast(error.message, "error");
  } finally {
    fontSelect.disabled = false;
  }
}

function updateActiveFont() {
  const font = selectedFont();
  $$(".font-card").forEach((card) => card.classList.toggle("active", card.dataset.fontId === font?.id));
  if (font) $("#selected-font-sample").textContent = `${font.name}：今天也要认真写字`;
}

async function loadOpenFontStatus() {
  const status = $("#font-install-status");
  const button = $("#download-open-fonts");
  try {
    const data = await apiJson("/api/open-fonts");
    const normal = data.available.filter((font) => font.category === "normal");
    const installed = new Set(data.installed.map((font) => font.filename));
    const missing = normal.filter((font) => !installed.has(font.filename));
    status.textContent = missing.length
      ? `待安装：${missing.map((font) => font.family).join("、")}`
      : `已安装 ${normal.length} 款 OFL 回退字体`;
    status.className = `status-line${missing.length ? "" : " success"}`;
    button.textContent = missing.length ? `安装 ${missing.length} 款` : "重新检查";
    button.dataset.missing = String(missing.length);
  } catch (error) {
    status.textContent = error.message;
    status.className = "status-line error";
    button.textContent = "重新检查";
  }
}

async function downloadOpenFonts() {
  const button = $("#download-open-fonts");
  button.disabled = true;
  button.textContent = "检查中…";
  try {
    const data = await apiJson("/api/open-fonts/download", { method: "POST" });
    if (data.failed?.length) throw new Error("部分字体下载失败，请检查网络后重试");
    await Promise.all([loadFonts(fontSelect.value), loadOpenFontStatus()]);
    showToast("正常手写字体已可使用", "success");
  } catch (error) {
    showToast(error.message, "error");
    await loadOpenFontStatus();
  } finally {
    button.disabled = false;
  }
}

async function loadHealth() {
  try {
    const data = await apiJson("/api/health");
    setServiceState("online", `${data.fonts} 款字体可用`);
  } catch {
    setServiceState("offline", "本地服务未连接");
  }
}

function collectSettings() {
  return {
    scene_mode: selectedValue("scene-mode", "desk_photo"),
    style_profile: "clean",
    paper_style: state.paperStyle,
    page_width: numberValue("#page-width"),
    page_height: numberValue("#page-height"),
    use_background_size: $("#use-background-size").checked,
    direct_background: Boolean(state.paperUrl),
    margin_left: numberValue("#margin-left"),
    margin_right: numberValue("#margin-right"),
    margin_top: numberValue("#margin-top"),
    margin_bottom: numberValue("#margin-bottom"),
    font_size: numberValue("#font-size"),
    line_height: numberValue("#line-height"),
    char_spacing: numberValue("#char-spacing"),
    paragraph_spacing: numberValue("#paragraph-spacing"),
    position_jitter: numberValue("#position-jitter"),
    rotation_jitter: numberValue("#rotation-jitter"),
    size_jitter: numberValue("#size-jitter"),
    baseline_jitter: numberValue("#baseline-jitter"),
    line_slope_jitter: numberValue("#line-slope-jitter"),
    correction_rate: numberValue("#correction-rate"),
    ink_density: numberValue("#ink-density"),
    ink_color: selectedValue("ink-color", "#202324"),
    seed: numberValue("#seed"),
    max_pages: 12,
  };
}

function updateLiveTypography() {
  const fontSize = numberValue("#font-size");
  const lineHeight = numberValue("#line-height");
  const pageWidth = Math.max(1, numberValue("#page-width"));
  const pageHeight = Math.max(1, numberValue("#page-height"));
  const directTemplate = studio.classList.contains("direct-template");
  let templateScale;
  if (directTemplate) {
    const availableWidth = Math.max(1, studio.clientWidth - 56);
    const availableHeight = Math.max(1, studio.clientHeight - 56);
    templateScale = Math.min(availableWidth / pageWidth, availableHeight / pageHeight);
    paper.style.width = `${Math.round(pageWidth * templateScale)}px`;
    paper.style.height = `${Math.round(pageHeight * templateScale)}px`;
  } else {
    paper.style.removeProperty("height");
    paper.style.removeProperty("width");
    templateScale = Math.max(0.1, paper.clientWidth / pageWidth);
  }
  paper.style.setProperty("--preview-size", `${Math.max(12, fontSize * templateScale)}px`);
  paper.style.setProperty("--preview-line", String(Math.max(1.15, lineHeight / Math.max(fontSize, 1))));
  paper.style.setProperty("--preview-spacing", `${numberValue("#char-spacing") * templateScale}px`);
  paper.style.setProperty("--paper-line", `${Math.max(30, lineHeight * 0.72)}px`);
  paper.style.color = selectedValue("ink-color", "#202324");
  paperContent.style.padding = ["#margin-top", "#margin-right", "#margin-bottom", "#margin-left"]
    .map((selector) => `${Math.max(0, numberValue(selector) * templateScale)}px`)
    .join(" ");
}

function updateRangeOutputs() {
  $("#position-jitter-value").textContent = numberValue("#position-jitter").toFixed(1);
  $("#rotation-jitter-value").textContent = `${numberValue("#rotation-jitter").toFixed(1)}°`;
  $("#size-jitter-value").textContent = numberValue("#size-jitter").toFixed(1);
  $("#baseline-jitter-value").textContent = numberValue("#baseline-jitter").toFixed(1);
  $("#ink-density-value").textContent = `${Math.round(numberValue("#ink-density") * 100)}%`;
}

function setZoom(value) {
  state.zoom = Math.max(40, Math.min(120, value));
  $("#zoom-value").textContent = `${state.zoom}%`;
  paper.style.setProperty("--paper-zoom", state.zoom / 100);
  resultImage.style.setProperty("--result-zoom", state.zoom / 72);
}

function clearResult(announce = false) {
  state.result = null;
  state.currentPage = 0;
  resultImage.hidden = true;
  resultImage.removeAttribute("src");
  paper.hidden = false;
  $("#result-meta").textContent = "实时样式";
  $("#page-strip").innerHTML = '<div class="page-thumb live active"><span>实时</span></div>';
  setDownloads(null);
  if (announce) showToast("生成结果已清除");
}

function showPage(index) {
  if (!state.result?.pages?.[index]) return;
  state.currentPage = index;
  resultImage.src = state.result.pages[index].url;
  resultImage.hidden = false;
  paper.hidden = true;
  $("#result-meta").textContent = `第 ${index + 1} / ${state.result.page_count} 页`;
  $$(".page-thumb[data-page]").forEach((button) => {
    button.classList.toggle("active", Number(button.dataset.page) === index);
  });
  setDownloads(state.result);
}

function renderPageStrip(data) {
  const strip = $("#page-strip");
  strip.replaceChildren();
  data.pages.forEach((pageData, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "page-thumb";
    button.dataset.page = String(index);
    const image = document.createElement("img");
    image.src = pageData.url;
    image.alt = `第 ${index + 1} 页`;
    image.loading = "lazy";
    button.appendChild(image);
    button.addEventListener("click", () => showPage(index));
    strip.appendChild(button);
  });
}

async function submitRender(event) {
  event.preventDefault();
  const mode = selectedValue("input-mode", "file");
  let documentFile = state.documentFile;
  if (mode === "text") {
    const text = $("#direct-text").value.trim();
    if (!text) {
      showToast("请先输入需要转换的文字", "error");
      $("#direct-text").focus();
      return;
    }
    documentFile = new File([text], "handdraft-input.txt", { type: "text/plain" });
  }
  if (!documentFile) {
    showToast("请先选择 Markdown、TXT 或 Word 文档", "error");
    $("#document").click();
    return;
  }
  if (!fontSelect.value && !state.fontUpload) {
    showToast("请先选择或上传手写字体", "error");
    return;
  }

  const payload = new FormData();
  payload.append("document", documentFile, documentFile.name);
  payload.append("settings", JSON.stringify(collectSettings()));
  payload.append("font_id", fontSelect.value || "");
  const background = $("#background").files?.[0];
  if (background) payload.append("background", background, background.name);
  if (state.fontUpload) payload.append("font_upload", state.fontUpload, state.fontUpload.name);

  setLoading(true);
  setSaveState("正在本机生成手写页面");
  try {
    const data = await apiJson("/api/render", { method: "POST", body: payload });
    state.result = data;
    state.currentPage = 0;
    renderPageStrip(data);
    showPage(0);
    setSaveState(`已生成 ${data.page_count} 页 · 文件保存在本机`);
    showToast(`已生成 ${data.page_count} 页手写文稿`, "success");
  } catch (error) {
    setSaveState("生成失败 · 请检查输入");
    showToast(error.message, "error");
  } finally {
    setLoading(false);
  }
}

async function loadUploadedFont(file) {
  if (!file) return;
  if (!/\.(ttf|otf|ttc)$/i.test(file.name)) {
    showToast("请上传 TTF、OTF 或 TTC 字体", "error");
    return;
  }
  state.fontUpload = file;
  const family = `HandDraft-Upload-${Date.now()}`;
  const url = URL.createObjectURL(file);
  try {
    const face = await new FontFace(family, `url("${url}")`).load();
    document.fonts.add(face);
    paper.style.setProperty("--preview-font", `"${family}"`);
    $("#selected-font-sample").style.fontFamily = family;
    $("#selected-font-sample").textContent = `${filenameWithoutExtension(file.name)}：今天也要认真写字`;
    const option = document.createElement("option");
    option.value = "";
    option.textContent = `${filenameWithoutExtension(file.name)} · 本次上传`;
    option.selected = true;
    fontSelect.prepend(option);
    $$(".font-card").forEach((card) => card.classList.remove("active"));
    $("#font-install-status").textContent = `本次将使用 ${file.name}`;
    showToast("字体已载入，仅用于本次生成", "success");
  } catch {
    state.fontUpload = null;
    showToast("无法读取这个字体文件", "error");
  } finally {
    URL.revokeObjectURL(url);
  }
}

function resetWorkspace() {
  form.reset();
  state.documentFile = null;
  state.fontUpload = null;
  revokeObjectUrl("paperUrl");
  state.paperStyle = "reference_blank_desk";
  $("#document-name").textContent = "选择 Markdown 或 Word";
  $("#background-name").textContent = "上传一张带纸张与环境的图片";
  $("#direct-text").hidden = true;
  $("#document-drop").hidden = false;
  setProjectName("未命名文稿");
  setSaveState("本地处理 · 未上传服务器");
  updatePaperText();
  applyTemplateLayout(PAPER_TEMPLATE_LAYOUTS[state.paperStyle]);
  updatePaperAppearance();
  updateSceneAppearance();
  updateRangeOutputs();
  updateLiveTypography();
  setZoom(72);
  clearResult(false);
  loadFonts().catch(() => {});
  loadOpenFontStatus().catch(() => {});
  showToast("工作台已重置");
}

async function checkAiEndpoint() {
  const keyInput = $("#ai-key");
  const status = $("#ai-status");
  const button = $("#ai-check");
  const apiKey = keyInput.value.trim();
  if (!apiKey) {
    status.textContent = "请先填写 API Key；密钥不会被保存。";
    keyInput.focus();
    return;
  }
  button.disabled = true;
  status.textContent = "正在检查本地预留接口…";
  try {
    const data = await apiJson("/api/ai/glyph-kit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        provider: $("#ai-provider").value.trim(),
        model: $("#ai-model").value.trim(),
        apiKey,
      }),
    });
    status.textContent = `${data.message} 密钥回显：${data.key_hint}`;
  } catch (error) {
    status.textContent = error.message;
  } finally {
    keyInput.value = "";
    button.disabled = false;
  }
}

function bindEvents() {
  form.addEventListener("submit", submitRender);
  $("#document").addEventListener("change", (event) => setDocument(event.target.files?.[0] || null));
  $("#background").addEventListener("change", (event) => setCustomBackground(event.target.files?.[0] || null));
  $("#font-upload").addEventListener("change", (event) => loadUploadedFont(event.target.files?.[0]));
  $("#refresh-fonts").addEventListener("click", () => loadFonts(fontSelect.value));
  $("#download-open-fonts").addEventListener("click", downloadOpenFonts);
  $("#clear-result").addEventListener("click", () => clearResult(true));
  $("#reset-workspace").addEventListener("click", resetWorkspace);
  $("#header-export").addEventListener("click", () => downloadLinks.pdf.click());
  $("#zoom-out").addEventListener("click", () => setZoom(state.zoom - 8));
  $("#zoom-in").addEventListener("click", () => setZoom(state.zoom + 8));

  $$("input[name='input-mode']").forEach((input) => {
    input.addEventListener("change", () => switchInputMode(input.value));
  });
  $("#direct-text").addEventListener("input", (event) => {
    updatePaperText(event.target.value || DEFAULT_PREVIEW);
    setSaveState();
  });
  fontSelect.addEventListener("change", () => {
    state.fontUpload = null;
    updateActiveFont();
    updateFontPreview();
    setSaveState();
  });

  const drop = $("#document-drop");
  for (const name of ["dragenter", "dragover"]) {
    drop.addEventListener(name, (event) => {
      event.preventDefault();
      drop.classList.add("dragging");
    });
  }
  for (const name of ["dragleave", "drop"]) {
    drop.addEventListener(name, (event) => {
      event.preventDefault();
      drop.classList.remove("dragging");
    });
  }
  drop.addEventListener("drop", (event) => {
    const file = event.dataTransfer?.files?.[0];
    if (!file || !/\.(md|markdown|txt|doc|docx)$/i.test(file.name)) {
      showToast("仅支持 Markdown、TXT、DOCX 或 DOC 文档", "error");
      return;
    }
    setDocument(file);
  });

  $$(".paper-preset").forEach((button) => {
    button.addEventListener("click", () => {
      revokeObjectUrl("paperUrl");
      $("#background").value = "";
      $("#background-name").textContent = "上传一张带纸张与环境的图片";
      state.paperStyle = button.dataset.paper;
      const layout = PAPER_TEMPLATE_LAYOUTS[state.paperStyle];
      if (layout) {
        applyTemplateLayout(layout);
      }
      updatePaperAppearance();
      updateSceneAppearance();
      updateLiveTypography();
      setSaveState();
    });
  });
  $$("input[name='scene-mode']").forEach((input) => {
    input.addEventListener("change", () => {
      updateSceneAppearance();
      setSaveState();
    });
  });

  const liveControls = [
    "#font-size", "#line-height", "#char-spacing", "#paragraph-spacing",
    "#page-width", "#page-height", "#margin-left", "#margin-right", "#margin-top", "#margin-bottom",
    "#position-jitter", "#rotation-jitter", "#size-jitter", "#baseline-jitter", "#ink-density",
  ];
  for (const selector of liveControls) {
    $(selector).addEventListener("input", () => {
      updateRangeOutputs();
      updatePaperAppearance();
      updateLiveTypography();
      setSaveState();
    });
  }
  $$("input[name='ink-color']").forEach((input) => input.addEventListener("change", updateLiveTypography));

  $$(".rail-tool[data-target]").forEach((button) => {
    button.addEventListener("click", () => {
      $$(".rail-tool").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      $(`#${button.dataset.target}`).scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });

  $("#open-ai").addEventListener("click", () => $("#ai-dialog").showModal());
  $("#clear-key").addEventListener("click", () => {
    $("#ai-key").value = "";
    $("#ai-status").textContent = "密钥已清空，浏览器不会保存它。";
  });
  $("#ai-check").addEventListener("click", checkAiEndpoint);
  window.addEventListener("beforeunload", () => {
    revokeObjectUrl("paperUrl");
    $("#ai-key").value = "";
  });
  window.addEventListener("resize", updateLiveTypography);
}

async function initialize() {
  if (window.lucide) window.lucide.createIcons();
  bindEvents();
  applyTemplateLayout(PAPER_TEMPLATE_LAYOUTS[state.paperStyle]);
  updatePaperText();
  updatePaperAppearance();
  updateSceneAppearance();
  updateRangeOutputs();
  updateLiveTypography();
  setZoom(72);
  setDownloads(null);
  await Promise.all([loadHealth(), loadFonts(), loadOpenFontStatus()]);
}

initialize();
