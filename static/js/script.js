document.addEventListener('DOMContentLoaded', () => {
    document.querySelector('.decrement-number').addEventListener('click', () => {
        console.log('click -');
        let val = document.querySelector('input[name="title"]').value;
        val = val.replace(/(\d+)$/, (number) => parseInt(number, 10) - 1);
        document.querySelector('input[name="title"]').value = val;
    });
    document.querySelector('.increment-number').addEventListener('click', () => {
        console.log('click +');
        let val = document.querySelector('input[name="title"]').value;
        val = val.replace(/(\d+)$/, (number) => parseInt(number, 10) + 1);
        document.querySelector('input[name="title"]').value = val;
    });
});