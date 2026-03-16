import gradio as gr


def convert(temperature: str, direction: str, history: list) -> tuple:
    if temperature.strip() == "":
        return (
            "",
            gr.update(value="⚠️ Please enter a temperature value.", visible=True),
        )

    try:
        value = float(temperature.replace(",", "."))
    except ValueError:
        return (
            "",
            gr.update(value=f"⚠️ '{temperature}' is not a valid number.", visible=True),
        )

    # Sanity-check: absolute zero is the hard physical lower bound
    if direction == "Celsius → Fahrenheit" and value < -273.15:
        return (
            "",
            gr.update(
                value="⚠️ Temperature below absolute zero (−273.15 °C) is impossible.",
                visible=True,
            ),
        )
    if direction == "Fahrenheit → Celsius" and value < -459.67:
        return (
            "",
            gr.update(
                value="⚠️ Temperature below absolute zero (−459.67 °F) is impossible.",
                visible=True,
            ),
        )

    # ── Conversion ────────────────────────────────────────────────────────────
    if direction == "Celsius → Fahrenheit":
        result = (value * 9 / 5) + 32
        result_text = f"{value:.2f} °C  =  {result:.2f} °F"
    else:
        result = (value - 32) * 5 / 9
        result_text = f"{value:.2f} °F  =  {result:.2f} °C"

    return result_text, gr.update(value="", visible=False)


with gr.Blocks(
    title="🌡️ Temperature Converter", theme=gr.themes.Monochrome(font="sans-serif")
) as demo:
    gr.Markdown("# 🌡️ Temperature Converter")
    with gr.Row():
        with gr.Column(scale=2):
            temperature_input = gr.Textbox(
                label="Temperature",
                placeholder="e.g. 100  or  -40.5",
                autofocus=True,
            )
            direction_input = gr.Radio(
                choices=["Celsius → Fahrenheit", "Fahrenheit → Celsius"],
                value="Celsius → Fahrenheit",
                label="Conversion direction",
            )
            with gr.Row():
                convert_btn = gr.Button(
                    "Convert",
                    variant="primary",
                )

            error_output = gr.Textbox(
                label="",
                interactive=False,
                show_label=False,
                visible=False,
                lines=1,
            )

        with gr.Column(scale=1):
            result_output = gr.Textbox(
                label="Result",
                interactive=False,
                lines=2,
            )

    convert_inputs = [temperature_input, direction_input]
    convert_outputs = [result_output, error_output]

    callback = (convert, convert_inputs, convert_outputs)

    convert_btn.click(*callback)

    # Also trigger on Enter key inside the textbox
    temperature_input.submit(*callback)

demo.launch()
