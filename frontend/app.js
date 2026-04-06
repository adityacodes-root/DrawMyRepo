"use strict";
document.addEventListener("DOMContentLoaded", () => {
    mermaid.initialize({ startOnLoad: false, theme: 'default', securityLevel: 'loose' });
    const generateBtn = document.getElementById("generate-btn");
    const repoUrlInput = document.getElementById("repo-url");
    const archModeSelect = document.getElementById("arch-mode");
    const loadingDiv = document.getElementById("loading");
    const errorDiv = document.getElementById("error");
    const mermaidRenderContainer = document.getElementById("mermaid-render");
    const copyBtn = document.getElementById("copy-btn");
    const downloadBtn = document.getElementById("download-btn");
    const expPanel = document.getElementById("exp-panel");
    const expHeader = document.getElementById("exp-header");
    const expContent = document.getElementById("exp-content");
    const navVisualizer = document.getElementById("nav-visualizer");
    const navHistory = document.getElementById("nav-history");
    const visualizerSection = document.getElementById("visualizer-section");
    const historySection = document.getElementById("history-section");
    const historyList = document.getElementById("history-list");
    if (!generateBtn || !repoUrlInput || !mermaidRenderContainer)
        return;
    let currentMermaidCode = "";
    if (navVisualizer && navHistory && visualizerSection && historySection && historyList) {
        navVisualizer.addEventListener("click", () => {
            historySection.style.display = "none";
            visualizerSection.style.display = "block";
            navVisualizer.classList.add("text-blue-700", "font-bold");
            navVisualizer.classList.remove("text-stone-600");
            navHistory.classList.remove("text-blue-700", "font-bold");
            navHistory.classList.add("text-stone-600");
        });
        navHistory.addEventListener("click", async () => {
            visualizerSection.style.display = "none";
            historySection.style.display = "block";
            navHistory.classList.add("text-blue-700", "font-bold");
            navHistory.classList.remove("text-stone-600");
            navVisualizer.classList.remove("text-blue-700", "font-bold");
            navVisualizer.classList.add("text-stone-600");
            historyList.innerHTML = '<div class="p-4 font-clean animate-pulse">Loading history...</div>';
            try {
                const res = await fetch("http://127.0.0.1:8010/history");
                const items = await res.json();
                historyList.innerHTML = items.length ? '' : '<div class="p-4 font-clean">No history found.</div>';
                items.forEach((item) => {
                    const block = document.createElement("div");
                    block.className = "sketch-border p-4 bg-surface cursor-pointer hover:bg-surface-variant transition-colors rotate-1 mb-3";
                    block.innerHTML = `<p class="font-handwritten text-xl font-bold truncate">${item.repo_url}</p><p class="font-clean text-sm opacity-70">Mode: ${item.mode}</p>`;
                    block.addEventListener("click", () => {
                        repoUrlInput.value = item.repo_url;
                        if (archModeSelect)
                            archModeSelect.value = item.mode;
                        navVisualizer.click();
                        generateBtn.click();
                    });
                    historyList.appendChild(block);
                });
            }
            catch (err) {
                historyList.innerHTML = '<div class="p-4 font-clean text-error">Failed to load history</div>';
            }
        });
    }
    if (expHeader && expContent) {
        expHeader.addEventListener("click", () => {
            const isHidden = expContent.style.display === "none" || expContent.style.display === "";
            expContent.style.display = isHidden ? "block" : "none";
            const icon = expHeader.querySelector("span:last-child");
            if (icon) {
                icon.textContent = isHidden ? "keyboard_arrow_up" : "keyboard_arrow_down";
            }
        });
    }
    if (copyBtn) {
        copyBtn.addEventListener("click", async () => {
            try {
                await navigator.clipboard.writeText(currentMermaidCode);
                const original = copyBtn.innerHTML;
                copyBtn.innerHTML = `<span class="material-symbols-outlined text-xl">check</span> Copied!`;
                setTimeout(() => copyBtn.innerHTML = original, 2000);
            }
            catch (err) {
                console.error("Clipboard write failed", err);
            }
        });
    }
    if (downloadBtn) {
        downloadBtn.addEventListener("click", () => {
            const svg = document.querySelector("#mermaid-render svg");
            if (!svg)
                return;
            const serializer = new XMLSerializer();
            const output = serializer.serializeToString(svg);
            const blob = new Blob([output], { type: "image/svg+xml;charset=utf-8" });
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = "architecture.svg";
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        });
    }
    generateBtn.addEventListener("click", async () => {
        const url = repoUrlInput.value.trim();
        if (!url)
            return;
        if (errorDiv)
            errorDiv.style.display = "none";
        if (expPanel)
            expPanel.style.display = "none";
        if (expContent)
            expContent.style.display = "none";
        mermaidRenderContainer.innerHTML = "";
        mermaidRenderContainer.removeAttribute("data-processed");
        if (loadingDiv)
            loadingDiv.style.display = "block";
        generateBtn.disabled = true;
        try {
            const mode = archModeSelect ? archModeSelect.value : "default";
            const response = await fetch("http://127.0.0.1:8010/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ repo_url: url, mode: mode })
            });
            const data = await response.json();
            if (!response.ok)
                throw new Error(data.detail || "Analysis failed");
            currentMermaidCode = data.mermaid_code;
            const id = "mermaid-svg-" + Date.now();
            try {
                const renderResult = await mermaid.render(id, data.mermaid_code);
                mermaidRenderContainer.innerHTML = renderResult.svg;
            }
            catch (err) {
                console.error(err);
                throw new Error("Mermaid format error.");
            }
            mermaidRenderContainer.classList.add("p-8", "block");
            mermaidRenderContainer.classList.remove("flex", "flex-col", "items-center", "justify-center");
            setTimeout(() => {
                const svgElement = mermaidRenderContainer.querySelector("svg");
                if (svgElement) {
                    svgElement.removeAttribute("max-width");
                    svgElement.style.maxWidth = "none";
                    svgElement.style.width = "100%";
                    svgElement.style.height = "100%";
                    try {
                        svgPanZoom(svgElement, {
                            zoomEnabled: true,
                            controlIconsEnabled: true,
                            fit: true,
                            center: true,
                            minZoom: 0.1,
                            maxZoom: 10
                        });
                    }
                    catch (e) {
                        console.error("PanZoom initialization failed", e);
                    }
                }
            }, 50);
            if (data.explanation && expContent && expPanel) {
                expContent.textContent = data.explanation;
                expPanel.style.display = "block";
            }
        }
        catch (err) {
            if (errorDiv) {
                errorDiv.textContent = err.message || "An error occurred";
                errorDiv.style.display = "block";
            }
        }
        finally {
            if (loadingDiv)
                loadingDiv.style.display = "none";
            generateBtn.disabled = false;
        }
    });
});
