const form = document.getElementById('emailForm');
const fileInput = document.getElementById('fileInput');
const textInput = document.getElementById('textInput');
const submitBtn = document.getElementById('submitBtn');
const historyBtn = document.getElementById('historyBtn');
const spinner = document.getElementById('spinner');
const resultBox = document.getElementById('result');
const categoryEl = document.getElementById('category');
const suggestedEl = document.getElementById('suggested');
const previewEl = document.getElementById('preview');
const copyBtn = document.getElementById('copyBtn');

function renderHistoryTable(data) {
  if (!data.length) {
    document.getElementById("history").innerHTML = "<p>Nenhum histórico encontrado.</p>";
    return;
  }

  let html = `<table class="table table-bordered">
    <thead>
      <tr>
        <th>ID</th>
        <th>Texto</th>
        <th>Categoria</th>
        <th>Resposta</th>
        <th>Data</th>
      </tr>
    </thead>
    <tbody>`;

  data.forEach(e => {
    html += `<tr>
      <td>${e.id}</td>
      <td>${e.texto}</td>
      <td style="color:${e.categoria === 'Produtivo' ? 'green' : 'gray'}"><b>${e.categoria}</b></td>
      <td>${e.resposta}</td>
      <td>${new Date(e.created_at).toLocaleString()}</td>
    </tr>`;
  });

  html += "</tbody></table>";
  document.getElementById("history").innerHTML = html;
}

historyBtn.onclick = async () => {
  const res = await fetch("/api/history");
  const data = await res.json();
  renderHistoryTable(data);
};

document.getElementById("filterBtn").onclick = async () => {
  const params = new URLSearchParams({
    keyword: document.getElementById("filterKeyword").value,
    category: document.getElementById("filterCategory").value,
    start_date: document.getElementById("filterStartDate").value,
    end_date: document.getElementById("filterEndDate").value
  }).toString();

  const res = await fetch("/api/history?" + params);
  const data = await res.json();
  renderHistoryTable(data);
};

function exportHistory(type) {
  const params = new URLSearchParams({
    keyword: document.getElementById("filterKeyword").value,
    category: document.getElementById("filterCategory").value,
    start_date: document.getElementById("filterStartDate").value,
    end_date: document.getElementById("filterEndDate").value
  }).toString();

  window.open(`/api/history/export/${type}?${params}`, "_blank");
}

document.getElementById("exportCsvBtn").onclick = () => exportHistory("csv");
document.getElementById("exportPdfBtn").onclick = () => exportHistory("pdf");

// Envio do e-mail
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  submitBtn.disabled = true;
  spinner.classList.remove('d-none');
  resultBox.style.display = 'none';

  const fd = new FormData();
  if (fileInput.files.length > 0) fd.append('file', fileInput.files[0]);
  const text = textInput.value.trim();
  if (text.length > 0) fd.append('text', text);

  try {
    const res = await fetch("/api/classify", {
      method: 'POST',
      body: fd
    });

    if (!res.ok) {
      const err = await res.json();
      alert("Erro: " + (err.error || res.statusText));
      return;
    }

    const data = await res.json();
    categoryEl.textContent = data.categoria;
    categoryEl.style.color = data.categoria === "Produtivo" ? "green" : "gray";
    suggestedEl.textContent = data.resposta;
    previewEl.textContent = data.texto;
    resultBox.style.display = 'block';

    fileInput.value = "";
    textInput.value = "";

  } catch (err) {
    console.error(err);
    alert('Erro de comunicação com o servidor.');
  } finally {
    submitBtn.disabled = false;
    spinner.classList.add('d-none');
  }
});

copyBtn.addEventListener('click', () => {
  const textToCopy = suggestedEl.textContent.trim();
  if (!textToCopy) {
    alert("Não há texto para copiar!");
    return;
  }

  navigator.clipboard.writeText(textToCopy).then(() => {
    copyBtn.textContent = "Copiado!";
    setTimeout(() => copyBtn.textContent = "Copiar", 1500);
  }).catch(err => {
    console.error("Erro ao copiar: ", err);
    alert("Erro ao copiar o texto");
  });
});
