document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('uploadForm');
    const uploadBtn = document.getElementById('uploadBtn');
    const processBtn = document.getElementById('processBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const resultArea = document.getElementById('resultArea');
    const resultTable = document.getElementById('resultTable');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressBar = uploadProgress.querySelector('.progress-bar');
    const totalItems = document.getElementById('totalItems');
    const processSpinner = processBtn.querySelector('.spinner-border');

    uploadForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const formData = new FormData(uploadForm);
        uploadProgress.classList.remove('d-none');
        uploadBtn.disabled = true;
        progressBar.style.width = '0%';

        try {
            // アップロード進捗のシミュレーション
            let progress = 0;
            const progressInterval = setInterval(() => {
                progress += 10;
                if (progress <= 90) {
                    progressBar.style.width = `${progress}%`;
                }
            }, 200);

            const response = await fetch('/upload/ifc', {
                method: 'POST',
                body: formData
            });

            clearInterval(progressInterval);

            // レスポンスがJSONでない場合のエラーハンドリング
            let data;
            try {
                data = await response.json();
            } catch (parseError) {
                throw new Error('サーバーからの応答が不正です。');
            }

            if (response.ok && data.success) {
                progressBar.style.width = '100%';
                setTimeout(() => {
                    uploadProgress.classList.add('d-none');
                    processBtn.disabled = false;
                    uploadBtn.disabled = false;
                }, 500);

                if (data.message) {
                    alert(data.message);
                }
            } else {
                throw new Error(data.message || 'アップロードに失敗しました。');
            }
        } catch (error) {
            uploadProgress.classList.add('d-none');
            uploadBtn.disabled = false;
            progressBar.style.width = '0%';
            alert(error.message || 'エラーが発生しました。');
        }
    });

    processBtn.addEventListener('click', async function() {
        try {
            processBtn.disabled = true;
            processSpinner.classList.remove('d-none');
            downloadBtn.disabled = true;
            resultArea.style.display = 'none';

            const response = await fetch('/choice/material', {
                method: 'POST'
            });

            const data = await response.json();

            if (data.success) {
                displayResults(data.materials);
                downloadBtn.disabled = false;
                resultArea.style.display = 'block';
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            alert('処理に失敗しました: ' + error.message);
        } finally {
            processBtn.disabled = false;
            processSpinner.classList.add('d-none');
        }
    });

    downloadBtn.addEventListener('click', async function() {
        try {
            downloadBtn.disabled = true;

            const response = await fetch('/download/csv', {
                method: 'POST'
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'material_list.csv';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                a.remove();
            } else {
                throw new Error('CSVのダウンロードに失敗しました');
            }
        } catch (error) {
            alert('エラーが発生しました: ' + error.message);
        } finally {
            downloadBtn.disabled = false;
        }
    });

    function displayResults(materials) {
        resultTable.innerHTML = '';
        materials.forEach(material => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${material.name || '-'}</td>
                <td>${material.element_type || '-'}</td>
                <td>${material.length ? material.length.toFixed(2) : '-'}</td>
                <td>${material.width ? material.width.toFixed(2) : '-'}</td>
                <td>${material.height ? material.height.toFixed(2) : '-'}</td>
            `;
            resultTable.appendChild(row);
        });
        totalItems.textContent = `${materials.length} 件`;
    }
});