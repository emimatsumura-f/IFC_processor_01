document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('uploadForm');
    const uploadBtn = document.getElementById('uploadBtn');
    const processBtn = document.getElementById('processBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const resetBtn = document.getElementById('resetBtn');
    const resultArea = document.getElementById('resultArea');
    const resultTable = document.getElementById('resultTable');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressBar = uploadProgress.querySelector('.progress-bar');
    const totalItems = document.getElementById('totalItems');
    const processSpinner = processBtn.querySelector('.spinner-border');

    // 新規ファイル選択ボタンのイベントハンドラ
    resetBtn.addEventListener('click', function() {
        uploadForm.reset();
        uploadBtn.disabled = false;
        processBtn.disabled = true;
        downloadBtn.disabled = true;
        resultArea.style.display = 'none';
        uploadProgress.classList.add('d-none');
        progressBar.style.width = '0%';
        progressBar.setAttribute('aria-valuenow', 0);
    });

    uploadForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const file = document.getElementById('ifc_file').files[0];
        if (!file) {
            alert('ファイルを選択してください。');
            return;
        }

        // ファイルサイズチェック (200MB)
        const maxSize = 200 * 1024 * 1024;
        if (file.size > maxSize) {
            alert('ファイルサイズが大きすぎます（上限: 200MB）');
            return;
        }

        const formData = new FormData(uploadForm);
        uploadProgress.classList.remove('d-none');
        uploadBtn.disabled = true;
        processBtn.disabled = true;
        downloadBtn.disabled = true;
        resetBtn.disabled = true;
        progressBar.style.width = '0%';
        progressBar.setAttribute('aria-valuenow', 0);

        try {
            const xhr = new XMLHttpRequest();
            xhr.upload.onprogress = function(e) {
                if (e.lengthComputable) {
                    const percentComplete = (e.loaded / e.total) * 100;
                    progressBar.style.width = percentComplete + '%';
                    progressBar.setAttribute('aria-valuenow', percentComplete);
                }
            };

            xhr.onload = function() {
                if (xhr.status === 200) {
                    const response = JSON.parse(xhr.responseText);
                    if (response.success) {
                        progressBar.style.width = '100%';
                        progressBar.setAttribute('aria-valuenow', 100);
                        setTimeout(() => {
                            uploadProgress.classList.add('d-none');
                            processBtn.disabled = false;
                        }, 500);

                        if (response.message) {
                            alert(response.message);
                        }
                    } else {
                        throw new Error(response.message || 'アップロードに失敗しました。');
                    }
                } else {
                    throw new Error('アップロードに失敗しました。');
                }
            };

            xhr.onerror = function() {
                throw new Error('ネットワークエラーが発生しました。');
            };

            xhr.open('POST', '/upload/ifc', true);
            xhr.send(formData);

        } catch (error) {
            console.error('Upload error:', error);
            uploadProgress.classList.add('d-none');
            progressBar.style.width = '0%';
            progressBar.setAttribute('aria-valuenow', 0);
            alert(error.message || 'エラーが発生しました。時間をおいて再度お試しください。');
        } finally {
            uploadBtn.disabled = false;
            resetBtn.disabled = false;
        }
    });

    processBtn.addEventListener('click', async function() {
        try {
            processBtn.disabled = true;
            processSpinner.classList.remove('d-none');
            downloadBtn.disabled = true;
            resultArea.style.display = 'none';

            const response = await fetch('/choice/material', {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                throw new Error('サーバーからの応答が不正です（JSONではありません）');
            }

            const data = await response.json();
            if (data.success) {
                displayResults(data.materials);
                downloadBtn.disabled = false;
                resultArea.style.display = 'block';
                if (data.message) {
                    alert(data.message);
                }
            } else {
                throw new Error(data.message || '処理に失敗しました。');
            }
        } catch (error) {
            console.error('Processing error:', error);
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
                method: 'POST',
                headers: {
                    'Accept': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error('CSVのダウンロードに失敗しました');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'material_list.csv';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
        } catch (error) {
            console.error('Download error:', error);
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
                <td>${material.profile_type || '-'}</td>
                <td>${material.overall_depth ? material.overall_depth.toFixed(2) : '-'}</td>
                <td>${material.flange_width ? material.flange_width.toFixed(2) : (material.width ? material.width.toFixed(2) : '-')}</td>
                <td>${material.web_thickness ? material.web_thickness.toFixed(2) : '-'}</td>
                <td>${material.flange_thickness ? material.flange_thickness.toFixed(2) : '-'}</td>
                <td>${material.grade || '-'}</td>
                <td>${material.nominal_diameter || '-'}</td>
                <td>${material.length ? material.length.toFixed(2) : '-'}</td>
            `;
            resultTable.appendChild(row);
        });
        totalItems.textContent = `${materials.length} 件`;
    }
});