document.querySelectorAll("[id^='artisan-quote-form-']").forEach((form) => {
    const totalOutput = form.querySelector("[data-quote-total]");
    const amountFields = form.querySelectorAll("[data-quote-component]");

    const updateTotal = () => {
        const total = Array.from(amountFields).reduce((sum, field) => {
            const amount = Number.parseInt(field.value.replace(/\D/g, ""), 10);
            return sum + (Number.isFinite(amount) && amount > 0 ? amount : 0);
        }, 0);
        totalOutput.textContent = `Rp${new Intl.NumberFormat("id-ID").format(total)}`;
    };

    amountFields.forEach((field) => {
        field.addEventListener("input", () => {
            const value = field.value;
            const cursor = field.selectionStart ?? value.length;
            const digitsBeforeCursor = value.slice(0, cursor).replace(/\D/g, "").length;
            const digits = value.replace(/\D/g, "");
            const formatted = digits.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
            field.value = formatted;

            let nextCursor = 0;
            let countedDigits = 0;
            while (nextCursor < formatted.length && countedDigits < digitsBeforeCursor) {
                if (/\d/.test(formatted[nextCursor])) countedDigits += 1;
                nextCursor += 1;
            }
            field.setSelectionRange(nextCursor, nextCursor);
            updateTotal();
        });
    });
    updateTotal();
});
