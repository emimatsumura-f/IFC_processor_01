document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('uploadForm');
    const uploadBtn = document.getElementById('uploadBtn');
    const processBtn = document.getElementById('processBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const resultArea = document.getElementById('resultArea');
    const resultTable = document.getElementById('resultTable');

    uploadForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(uploadForm);
        
        try {
            const response = await fetch('/upload/ifc', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                processBtn.disabled = false;
                alert('ファイルのアップロードが完了しました。');
            } else {
                alert('アップロードに失敗しました: ' + data.message);
            }
        } catch (error) {
            alert('エラーが発生しました: ' + error);
        }
    });

    processBtn.addEventListener('click', async function() {
        try {
            const response = await fetch('/choice/material', {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                displayResults(data.materials);
                downloadBtn.disabled = false;
                resultArea.style.display = 'block';
            } else {
                alert('処理に失敗しました: ' + data.message);
            }
        } catch (error) {
            alert('エラーが発生しました: ' + error);
        }
    });

    downloadBtn.addEventListener('click', async function() {
        try {
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
                alert('CSVのダウンロードに失敗しました。');
            }
        } catch (error) {
            alert('エラーが発生しました: ' + error);
        }
    });

    function displayResults(materials) {
        resultTable.innerHTML = '';
        materials.forEach(material => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${material.name}</td>
                <td>${material.element_type}</td>
                <td>${material.length || '-'}</td>
                <td>${material.width || '-'}</td>
                <td>${material.height || '-'}</td>
            `;
            resultTable.appendChild(row);
        });
    }
});
