// D:\Nam2\ql_thuvien\static\js\script.js

document.addEventListener('DOMContentLoaded', (event) => {
    // Đoạn code này sẽ chạy khi toàn bộ HTML được tải xong
    console.log('✅ Hệ thống Thư viện đã tải tài nguyên JS thành công!');

    // Ví dụ: Hiệu ứng đơn giản khi click vào nút chi tiết (chỉ log ra console)
    const detailButtons = document.querySelectorAll('.btn-outline-primary');
    detailButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            // e.preventDefault(); // Uncomment nếu bạn không muốn chuyển trang
            const card = e.target.closest('.card');
            const title = card.querySelector('.card-title').textContent;
            console.log(`Đã bấm vào xem chi tiết sách: ${title}`);
        });
    });
});