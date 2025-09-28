const form = document.getElementById('emailForm')
const fileInput = document.getElementById('fileInput')
const textInput = document.getElementById('textInput')
const submitBtn = document.getElementById('submitBtn')
const spinner = document.getElementById('spinner')
const resultBox = document.getElementById('result')
const categoryEl = document.getElementById('category')
const confidenceEl = document.getElementById('confidence')
const keywordsEl = document.getElementById('keywords')
const suggestedEl = document.getElementById('suggested')
const previewEl = document.getElementById('preview')

form.addEventListener('submit', async (e) =>{
    e.preventDefault();
    submitBtn.disabled = true;
    spinner.classList.remove('d-none');
    resultBox.style.display = 'none';

    const fd = new FormData();
    if (fileInput.files.length > 0){
        fd.append('file', fileInput.files[0]);
    }
    const text = textInput.value.trim();
    if (text.length > 0){
        fd.append('text', text);
    }

    try{
        const res = await fetch("api/classify", {
            method: 'POST',
            body: fd
        });

        if (!res.ok){
            const err = await res.json();
            alert("Erro: " + (err.error || res.statusText))
            return;
        }

        const data = await res.json();
        categoryEl.textContent = data.category;
        confidenceEl.textContent = data.confidence;
        keywordsEl.textContent = JSON.stringify(data.matched_keywords, null, 2);
        suggestedEl.textContent = data.suggested_response;
        resultBox.style.display = 'block';
    } catch (err){
        console.error(err);
        alert('Erro de comunicação com o servidor.');
    } finally{
        submitBtn.disabled = false;
        spinner.classList.add('d-none');
    }
});