
const jsonObservationLayer = L.layerGroup().addTo(map);

async function loadJsonObservations() {
    try {
        const response = await fetch(
            "data/observations/manifest.json"
        );

        if (!response.ok) {
            throw new Error("Could not load observation manifest");
        }

        const manifest = await response.json();

        if (!Array.isArray(manifest.observations)) {
            throw new Error("Invalid observation manifest");
        }

        jsonObservationLayer.clearLayers();

        for (const filename of manifest.observations) {
            if (
                typeof filename !== "string" ||
                !/^[a-zA-Z0-9_-]+\.json$/.test(filename)
            ) {
                continue;
            }

            const observationResponse = await fetch(
                "data/observations/" + filename
            );

            if (!observationResponse.ok) continue;

            const observation = await observationResponse.json();

            if (
                observation.publication_consent !== true ||
                observation.verified !== true
            ) {
                continue;
            }

            const latitude = Number(observation.latitude);
            const longitude = Number(observation.longitude);

            if (
                !Number.isFinite(latitude) ||
                !Number.isFinite(longitude) ||
                latitude < -90 || latitude > 90 ||
                longitude < -180 || longitude > 180 ||
                observation.latitude == null ||
                observation.longitude == null ||
                observation.latitude === "" ||
                observation.longitude === ""
            ) {
                continue;
            }

            const marker = L.marker([latitude, longitude]);

            const popup = document.createElement("div");
            popup.className = "flood-observation-popup";

            const title = document.createElement("h3");
            title.textContent =
                observation.title || "Flood Observation";
            popup.appendChild(title);

            for (const [label, value] of [
                ["Event", observation.event_name],
                ["Date", observation.date],
                ["River", observation.river],
                ["Watershed", observation.watershed],
                ["Location", observation.location_name],
                ["Description", observation.description],
                ["Impacts", observation.impact],
                ["Photo credit", observation.photo_credit]
            ]) {
                if (value == null || value === "") continue;

                const paragraph = document.createElement("p");
                const strong = document.createElement("strong");
                strong.textContent = label + ": ";

                paragraph.appendChild(strong);
                paragraph.appendChild(
                    document.createTextNode(String(value))
                );

                popup.appendChild(paragraph);
            }

            if (
                typeof observation.photo === "string" &&
                /^\/?[a-zA-Z0-9/_-]+\.(jpg|jpeg|png|webp)$/i.test(
                    observation.photo
                ) &&
                !observation.photo.includes("..")
            ) {
                const image = document.createElement("img");

                image.src = observation.photo.startsWith("/")
                    ? observation.photo
                    : observation.photo;

                image.alt = "Flood observation photograph";
                image.loading = "lazy";
                image.style.maxWidth = "300px";
                image.style.width = "100%";

                popup.appendChild(image);
            }

            if (typeof observation.source_url === "string") {
                try {
                    const source = new URL(observation.source_url);

                    if (["http:", "https:"].includes(source.protocol)) {
                        const link = document.createElement("a");
                        link.href = source.href;
                        link.textContent = "View supporting source";
                        link.target = "_blank";
                        link.rel = "noopener noreferrer";
                        popup.appendChild(link);
                    }
                } catch (_) {
                    // Ignore invalid source URLs.
                }
            }

            marker.bindPopup(popup);
            marker.addTo(jsonObservationLayer);
        }

        console.log(
            "S4W JSON observation markers loaded:",
            jsonObservationLayer.getLayers().length
        );

    } catch (error) {
        console.error("JSON observation loading failed:", error);
    }
}

loadJsonObservations();
