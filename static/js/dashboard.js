function openChartModal(imgSrc) {
    document.getElementById('modal-chart-img').src = imgSrc;
    document.getElementById('chart-zoom-modal').style.display = 'flex';
}
function closeChartModal() {
    document.getElementById('chart-zoom-modal').style.display = 'none';
} 