// Dynamically load the navbar component into the page
document.addEventListener("DOMContentLoaded", async () => {
    const placeholder = document.getElementById("navbar-placeholder");
    if (!placeholder) return;

    try {
        const response = await fetch("/components/navbar.html");
        if (!response.ok) throw new Error("Failed to load navbar");
        const html = await response.text();
        placeholder.innerHTML = html;
        
        // Dispatch a custom event so shared.js knows the navbar is ready
        document.dispatchEvent(new Event("NavbarLoaded"));
    } catch (error) {
        console.error("Error loading navbar:", error);
    }
});
