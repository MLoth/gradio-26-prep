import gradio as gr
import httpx
import pandas as pd

BASE_URL = "http://127.0.0.1:8000"


# ── API helpers ───────────────────────────────────────────────────────────────


def fetch(path: str, params: dict | None = None) -> list[dict]:
    """GET from the API and return the JSON list, or [] on error."""
    try:
        response = httpx.get(f"{BASE_URL}{path}", params=params, timeout=5.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"API error: {e}")
        return []


def post(path: str, body: dict) -> dict | None:
    """POST to the API and return the created object, or None on error."""
    try:
        response = httpx.post(f"{BASE_URL}{path}", json=body, timeout=5.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"API error: {e}")
        return None


# ── Data loaders ──────────────────────────────────────────────────────────────


def load_species(conservation_status: str) -> pd.DataFrame:
    params = {}
    if conservation_status and conservation_status != "All":
        params["conservation_status"] = conservation_status

    data = fetch("/species/", params)

    if not data:
        return pd.DataFrame(
            columns=[
                "id",
                "name",
                "scientific_name",
                "family",
                "conservation_status",
                "wingspan_cm",
            ]
        )

    return pd.DataFrame(data)[
        [
            "id",
            "name",
            "scientific_name",
            "family",
            "conservation_status",
            "wingspan_cm",
        ]
    ]


def load_birds() -> pd.DataFrame:
    data = fetch("/birds/")

    if not data:
        return pd.DataFrame(columns=["id", "nickname", "ring_code", "age", "species"])

    rows = []
    for bird in data:
        rows.append(
            {
                "id": bird["id"],
                "nickname": bird["nickname"],
                "ring_code": bird["ring_code"],
                "age": bird["age"],
                "species": bird["species"]["name"],
            }
        )
    return pd.DataFrame(rows)


def load_spottings(observer_name: str) -> pd.DataFrame:
    params = {}
    if observer_name.strip():
        params["observer_name"] = observer_name.strip()

    data = fetch("/birdspotting/", params)

    if not data:
        return pd.DataFrame(
            columns=["id", "bird", "spotted_at", "location", "observer_name", "notes"]
        )

    rows = []
    for s in data:
        rows.append(
            {
                "id": s["id"],
                "bird": s["bird"]["nickname"],
                "spotted_at": s["spotted_at"],
                "location": s["location"],
                "observer_name": s["observer_name"],
                "notes": s["notes"] or "",
            }
        )
    return pd.DataFrame(rows)


# ── Species dropdown choices helper (for the Birds form) ──────────────────────


def get_species_choices() -> list[tuple[str, int]]:
    """Return a list of (display label, species_id) tuples for the dropdown."""
    data = fetch("/species/")
    return [(f"{s['name']} ({s['scientific_name']})", s["id"]) for s in data]


def get_bird_choices() -> list[tuple[str, int]]:
    """Return a list of (display label, bird_id) tuples for the dropdown."""
    data = fetch("/birds/")
    return [(f"{b['nickname']} [{b['ring_code']}]", b["id"]) for b in data]


def refresh_species_dropdown():
    return gr.update(choices=get_species_choices(), value=None)


def refresh_bird_dropdown():
    return gr.update(choices=get_bird_choices(), value=None)


# ── POST handlers ─────────────────────────────────────────────────────────────


def create_species(
    name: str,
    scientific_name: str,
    family: str,
    conservation_status: str,
    wingspan_cm: str,
) -> tuple:
    """Submit a new species to the API and return feedback + refreshed table."""
    if not all(
        [
            name.strip(),
            scientific_name.strip(),
            family.strip(),
            conservation_status,
            wingspan_cm.strip(),
        ]
    ):
        return gr.update(
            value="⚠️ All fields are required.", visible=True
        ), load_species("All")

    try:
        float(wingspan_cm.replace(",", "."))
    except ValueError:
        return gr.update(
            value=f"⚠️ '{wingspan_cm}' is not a valid wingspan.", visible=True
        ), load_species("All")

    body = {
        "name": name.strip(),
        "scientific_name": scientific_name.strip(),
        "family": family.strip(),
        "conservation_status": conservation_status,
        "wingspan_cm": wingspan_cm.strip(),
    }

    result = post("/species/", body)
    if result is None:
        return gr.update(
            value="❌ Failed to create species. Check the API.", visible=True
        ), load_species("All")

    return (
        gr.update(
            value=f"✅ Species '{result['name']}' created (id={result['id']}).",
            visible=True,
        ),
        load_species("All"),
    )


def create_bird(
    nickname: str,
    ring_code: str,
    age: int,
    species_id: int,
) -> tuple:
    """Submit a new bird to the API and return feedback + refreshed table."""
    if not all([nickname.strip(), ring_code.strip()]):
        return gr.update(
            value="⚠️ Nickname and ring code are required.", visible=True
        ), load_birds()

    if species_id is None:
        return gr.update(value="⚠️ Please select a species.", visible=True), load_birds()

    body = {
        "nickname": nickname.strip(),
        "ring_code": ring_code.strip(),
        "age": int(age),
        "species_id": int(species_id),
    }

    result = post("/birds/", body)
    if result is None:
        return gr.update(
            value="❌ Failed to create bird. Check the API.", visible=True
        ), load_birds()

    return (
        gr.update(
            value=f"✅ Bird '{result['nickname']}' created (id={result['id']}).",
            visible=True,
        ),
        load_birds(),
    )


def create_spotting(
    bird_id: int,
    spotted_at: str,
    location: str,
    observer_name: str,
    notes: str,
) -> tuple:
    """Submit a new sighting to the API and return feedback + refreshed table."""
    if not all([spotted_at.strip(), location.strip(), observer_name.strip()]):
        return gr.update(
            value="⚠️ Spotted at, location and observer name are required.", visible=True
        ), load_spottings("")

    if bird_id is None:
        return gr.update(value="⚠️ Please select a bird.", visible=True), load_spottings(
            ""
        )

    body = {
        "bird_id": int(bird_id),
        "spotted_at": spotted_at.strip(),
        "location": location.strip(),
        "observer_name": observer_name.strip(),
        "notes": notes.strip() if notes.strip() else None,
    }

    result = post("/birdspotting/", body)
    if result is None:
        return gr.update(
            value="❌ Failed to create sighting. Check the API.", visible=True
        ), load_spottings("")

    return (
        gr.update(
            value=f"✅ Sighting created (id={result['id']}) for bird '{result['bird']['nickname']}'.",
            visible=True,
        ),
        load_spottings(""),
    )


# ── UI ────────────────────────────────────────────────────────────────────────

with gr.Blocks(
    title="🐦 Birds Viewer", theme=gr.themes.Soft(primary_hue="blue")
) as demo:
    gr.Markdown("# 🐦 Birds Viewer")
    gr.Markdown("## Live data from the Birds API at `http://127.0.0.1:8000`.")

    with gr.Tabs():
        # ── Tab 1: Species ────────────────────────────────────────────────────
        with gr.Tab("Species"):
            with gr.Row():
                status_filter = gr.Dropdown(
                    choices=["All", "LC", "NT", "VU", "EN", "CR", "EW", "EX"],
                    value="All",
                    label="Filter by conservation status",
                    scale=2,
                )
                refresh_species_btn = gr.Button("🔄 Refresh", scale=1)

            species_table = gr.DataFrame(
                value=load_species("All"),
                label="Species",
                interactive=False,
            )

            with gr.Accordion("➕ Add new species", open=False):
                with gr.Row():
                    sp_name = gr.Textbox(
                        label="Name", placeholder="e.g. Atlantic Puffin"
                    )
                    sp_scientific = gr.Textbox(
                        label="Scientific name", placeholder="e.g. Fratercula arctica"
                    )
                with gr.Row():
                    sp_family = gr.Textbox(label="Family", placeholder="e.g. Alcidae")
                    sp_status = gr.Dropdown(
                        choices=["LC", "NT", "VU", "EN", "CR", "EW", "EX"],
                        label="Conservation status",
                    )
                    sp_wingspan = gr.Slider(
                        label="Wingspan (cm)", minimum=0, maximum=300, step=5, value=50
                    )
                sp_submit_btn = gr.Button("Create species", variant="primary")
                sp_feedback = gr.Textbox(
                    show_label=False, interactive=False, visible=False, lines=1
                )

            status_filter.change(
                fn=load_species, inputs=[status_filter], outputs=[species_table]
            )
            refresh_species_btn.click(
                fn=load_species, inputs=[status_filter], outputs=[species_table]
            )
            sp_submit_btn.click(
                fn=create_species,
                inputs=[sp_name, sp_scientific, sp_family, sp_status, sp_wingspan],
                outputs=[sp_feedback, species_table],
            )

        # ── Tab 2: Birds ──────────────────────────────────────────────────────
        with gr.Tab("Birds"):
            with gr.Row():
                refresh_birds_btn = gr.Button("🔄 Refresh")

            birds_table = gr.DataFrame(
                value=load_birds(),
                label="Birds",
                interactive=False,
            )

            with gr.Accordion("➕ Add new bird", open=False):
                with gr.Row():
                    b_nickname = gr.Textbox(
                        label="Nickname", placeholder="e.g. Skipper"
                    )
                    b_ring_code = gr.Textbox(
                        label="Ring code", placeholder="e.g. AB-1234"
                    )
                with gr.Row():
                    b_age = gr.Number(
                        label="Age (years)", value=0, minimum=0, precision=0
                    )
                    b_species = gr.Dropdown(
                        choices=get_species_choices(),
                        label="Species",
                    )
                with gr.Row():
                    b_refresh_species_btn = gr.Button(
                        "🔄 Refresh species list", scale=1
                    )
                    b_submit_btn = gr.Button("Create bird", variant="primary", scale=2)
                b_feedback = gr.Textbox(
                    show_label=False, interactive=False, visible=False, lines=1
                )

            refresh_birds_btn.click(fn=load_birds, inputs=[], outputs=[birds_table])
            b_refresh_species_btn.click(
                fn=refresh_species_dropdown, inputs=[], outputs=[b_species]
            )
            b_submit_btn.click(
                fn=create_bird,
                inputs=[b_nickname, b_ring_code, b_age, b_species],
                outputs=[b_feedback, birds_table],
            )

        # ── Tab 3: Sightings ──────────────────────────────────────────────────
        with gr.Tab("Sightings"):
            with gr.Row():
                observer_filter = gr.Textbox(
                    label="Filter by observer name",
                    placeholder="e.g. Jane",
                    scale=2,
                )
                refresh_spottings_btn = gr.Button("🔄 Refresh", scale=1)

            spottings_table = gr.DataFrame(
                value=load_spottings(""),
                label="Sightings",
                interactive=False,
            )

            with gr.Accordion("➕ Add new sighting", open=False):
                with gr.Row():
                    si_bird = gr.Dropdown(
                        choices=get_bird_choices(),
                        label="Bird",
                    )
                    si_refresh_birds_btn = gr.Button("🔄 Refresh bird list", scale=1)
                with gr.Row():
                    si_spotted_at = gr.Textbox(
                        label="Spotted at (ISO 8601)",
                        placeholder="e.g. 2024-06-01T09:30:00",
                    )
                    si_location = gr.Textbox(
                        label="Location", placeholder="e.g. Cliffs of Moher"
                    )
                with gr.Row():
                    si_observer = gr.Textbox(
                        label="Observer name", placeholder="e.g. Jane Doe"
                    )
                    si_notes = gr.Textbox(
                        label="Notes (optional)",
                        placeholder="e.g. Flying low over the water",
                    )
                si_submit_btn = gr.Button("Create sighting", variant="primary")
                si_feedback = gr.Textbox(
                    show_label=False, interactive=False, visible=False, lines=1
                )

            observer_filter.submit(
                fn=load_spottings, inputs=[observer_filter], outputs=[spottings_table]
            )
            refresh_spottings_btn.click(
                fn=load_spottings, inputs=[observer_filter], outputs=[spottings_table]
            )
            si_refresh_birds_btn.click(
                fn=refresh_bird_dropdown, inputs=[], outputs=[si_bird]
            )
            si_submit_btn.click(
                fn=create_spotting,
                inputs=[si_bird, si_spotted_at, si_location, si_observer, si_notes],
                outputs=[si_feedback, spottings_table],
            )


demo.launch()
