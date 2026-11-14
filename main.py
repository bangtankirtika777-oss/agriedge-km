import os
import numpy as np
from PIL import Image as PILImage

from kivy.app import App
from kivy.factory import Factory
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.image import Image
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.popup import Popup
from kivy.graphics.texture import Texture
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.utils import platform

from translations import ENGINE_TEXT_EN, NATIVE_TRANSLATIONS


def request_android_storage_permissions():
    if platform == 'android':
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_MEDIA_IMAGES
            ])
        except Exception:
            pass


request_android_storage_permissions()

Window.clearcolor = (0, 0.05, 0.1, 1)

# Maps each script family to built-in Android system fonts
SCRIPT_FONT_MAP = {
    "Odia": ["/system/fonts/NotoSansOriya-Regular.ttf", "/system/fonts/NotoSansOriyaUI-Regular.ttf"],
    "Devanagari": ["/system/fonts/NotoSansDevanagari-Regular.ttf", "/system/fonts/NotoSansDevanagariUI-Regular.ttf"],
    "Bengali": ["/system/fonts/NotoSansBengali-Regular.ttf", "/system/fonts/NotoSansBengaliUI-Regular.ttf"],
    "Telugu": ["/system/fonts/NotoSansTelugu-Regular.ttf", "/system/fonts/NotoSansTeluguUI-Regular.ttf"],
    "Tamil": ["/system/fonts/NotoSansTamil-Regular.ttf", "/system/fonts/NotoSansTamilUI-Regular.ttf"],
    "Gujarati": ["/system/fonts/NotoSansGujarati-Regular.ttf", "/system/fonts/NotoSansGujaratiUI-Regular.ttf"],
    "Kannada": ["/system/fonts/NotoSansKannada-Regular.ttf", "/system/fonts/NotoSansKannadaUI-Regular.ttf"],
    "Malayalam": ["/system/fonts/NotoSansMalayalam-Regular.ttf", "/system/fonts/NotoSansMalayalamUI-Regular.ttf"],
    "Gurmukhi": ["/system/fonts/NotoSansGurmukhi-Regular.ttf", "/system/fonts/NotoSansGurmukhiUI-Regular.ttf"],
    "Arabic": ["/system/fonts/NotoNaskhArabic-Regular.ttf", "/system/fonts/NotoSansArabic-Regular.ttf"],
    "CJK": ["/system/fonts/NotoSansCJK-Regular.ttc"],
    "OlChiki": ["/system/fonts/NotoSansOlChiki-Regular.ttf"]
}


def resolve_font_for_language(lang_label):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    local_custom = os.path.join(base_dir, "NotoSans-Regular.ttf")
    if os.path.exists(local_custom):
        return local_custom

    script_key = None
    if "Odia" in lang_label:
        script_key = "Odia"
    elif any(k in lang_label for k in ("Hindi", "Marathi", "Nepali", "Sanskrit", "Maithili", "Dogri", "Konkani", "Bodo")):
        script_key = "Devanagari"
    elif any(k in lang_label for k in ("Bengali", "Assamese", "Manipuri")):
        script_key = "Bengali"
    elif "Telugu" in lang_label:
        script_key = "Telugu"
    elif "Tamil" in lang_label:
        script_key = "Tamil"
    elif "Gujarati" in lang_label:
        script_key = "Gujarati"
    elif "Kannada" in lang_label:
        script_key = "Kannada"
    elif "Malayalam" in lang_label:
        script_key = "Malayalam"
    elif "Punjabi" in lang_label:
        script_key = "Gurmukhi"
    elif any(k in lang_label for k in ("Urdu", "Arabic", "Kashmiri", "Sindhi")):
        script_key = "Arabic"
    elif any(k in lang_label for k in ("Korean", "Mandarin")):
        script_key = "CJK"
    elif "Santali" in lang_label:
        script_key = "OlChiki"

    if script_key and script_key in SCRIPT_FONT_MAP:
        for path in SCRIPT_FONT_MAP[script_key]:
            if os.path.exists(path):
                return path

    if os.path.exists("/system/fonts/DroidSansFallback.ttf"):
        return "/system/fonts/DroidSansFallback.ttf"
    return "Roboto"


DEFAULT_FONT = resolve_font_for_language("Odia (ଓଡ଼ିଆ)")


class NativeSpinnerOption(SpinnerOption):
    def on_text(self, instance, value):
        self.font_name = resolve_font_for_language(value)


Factory.register('NativeSpinnerOption', cls=NativeSpinnerOption)


class SafeFileChooser(FileChooserIconView):
    def _generate_file_entries(self, *args, **kwargs):
        try:
            yield from super()._generate_file_entries(*args, **kwargs)
        except (PermissionError, OSError):
            return


def execute_layer1_construction_engine(file_path):
    try:
        pil_img = PILImage.open(file_path).convert("RGB")
    except Exception as err:
        raise ValueError(f"Layer 1 Error: Image file could not be read ({err}).")

    grid_w, grid_h = pil_img.size
    total_pixel_count = grid_h * grid_w

    lab_img = pil_img.convert("LAB")
    L_img, a_img, b_img = lab_img.split()

    L_shadow_channel = np.array(L_img, dtype=np.uint8)
    a_chroma_channel = np.array(a_img, dtype=np.uint8)
    b_chroma_channel = np.array(b_img, dtype=np.uint8)

    mean_lightness_index = float(np.mean(L_shadow_channel))

    a_resized = np.array(a_img.resize((224, 224)), dtype=np.uint8)
    b_resized = np.array(b_img.resize((224, 224)), dtype=np.uint8)
    final_layer1_output_matrix = np.stack([a_resized, b_resized], axis=-1)

    layer1_metrics = {
        "original_resolution": f"{grid_w} x {grid_h}",
        "total_pixel_count": total_pixel_count,
        "mean_lightness": round(mean_lightness_index, 2),
        "shadow_detected": mean_lightness_index < 85.0,
        "final_matrix_shape": final_layer1_output_matrix.shape
    }

    return final_layer1_output_matrix, layer1_metrics, a_chroma_channel, b_chroma_channel


WEATHER_MAP = {
    "Sunny / Dry Summer": "W_HOT",
    "Rainy / Humid Monsoon": "W_RAINY",
    "Cold / Moist Winter": "W_COLD"
}

LANGUAGES_LIST = sorted(["English"] + list(NATIVE_TRANSLATIONS.keys()))


def translate_via_ml_kit(text_token, target_lang):
    base_text = ENGINE_TEXT_EN.get(text_token, text_token)
    if target_lang == "English":
        return base_text
    if target_lang in NATIVE_TRANSLATIONS and text_token in NATIVE_TRANSLATIONS[target_lang]:
        return NATIVE_TRANSLATIONS[target_lang][text_token]
    return base_text


class AgriEdgeApp(App):
    def build(self):
        self.title = "Agri-Edge Native Oracle"
        self.active_lang = "English"
        self.current_font = "Roboto"
        self.selected_file_path = None
        self.animation_step = 0

        self.main_layout = BoxLayout(orientation='vertical', padding=15, spacing=10)

        self.anim_label = Label(
            text="On-Device Edge System Bootloader\nInitializing structural memory cache...",
            font_size='16sp',
            font_name=self.current_font,
            halign='center',
            valign='middle',
            bold=True
        )
        self.anim_label.bind(size=self.anim_label.setter('text_size'))
        self.main_layout.add_widget(self.anim_label)

        Clock.schedule_interval(self.execute_boot_loader_animation, 0.02)
        return self.main_layout

    def execute_boot_loader_animation(self, dt):
        self.animation_step += 1

        if self.animation_step < 35:
            self.anim_label.text = f"Seed Awakening ({self.animation_step}%)\nRoot expansion cracking soil boundary..."
            return True
        elif self.animation_step < 75:
            self.anim_label.text = f"Crop Swelling ({self.animation_step}%)\nPrimary root elongation driving downwards..."
            return True
        elif self.animation_step < 100:
            self.anim_label.text = f"Cellular Differentiation ({self.animation_step}%)\nAnchoring baseline established!"
            return True
        else:
            self.main_layout.remove_widget(self.anim_label)
            self.mount_main_workspace_dashboard()
            return False

    def mount_main_workspace_dashboard(self):
        self.header_label = Label(
            text=translate_via_ml_kit("workspace_title", self.active_lang),
            font_size='20sp',
            font_name=self.current_font,
            size_hint_y=0.1,
            bold=True
        )
        self.main_layout.add_widget(self.header_label)

        self.lang_spinner = Spinner(
            text="Select Language (32 Available)",
            values=LANGUAGES_LIST,
            font_name=DEFAULT_FONT,
            option_cls='NativeSpinnerOption',
            size_hint_y=0.08
        )
        self.lang_spinner.bind(text=self.on_language_change)
        self.main_layout.add_widget(self.lang_spinner)

        self.upload_btn = Button(
            text=translate_via_ml_kit("upload_lbl", self.active_lang),
            font_name=self.current_font,
            size_hint_y=0.08,
            background_color=(0, 0.4, 0.8, 1)
        )
        self.upload_btn.bind(on_press=self.open_file_chooser)
        self.main_layout.add_widget(self.upload_btn)

        self.preview_box = BoxLayout(orientation='horizontal', size_hint_y=0.25, spacing=5)
        self.img_ch_a = Image()
        self.img_ch_b = Image()
        self.preview_box.add_widget(self.img_ch_a)
        self.preview_box.add_widget(self.img_ch_b)
        self.main_layout.add_widget(self.preview_box)

        self.weather_label = Label(
            text=translate_via_ml_kit("weather_lbl", self.active_lang),
            font_name=self.current_font,
            size_hint_y=0.05,
            halign="left"
        )
        self.main_layout.add_widget(self.weather_label)

        self.weather_spinner = Spinner(
            text="Choose Weather",
            values=list(WEATHER_MAP.keys()),
            font_name=self.current_font,
            size_hint_y=0.08
        )
        self.weather_spinner.bind(text=self.execute_full_synthesis_pipeline)
        self.main_layout.add_widget(self.weather_spinner)

        self.console_output = Label(
            text="System Standby: Awaiting Soil Photo...",
font_name=self.current_font,
size_hint_y=0.3,
font_size='14sp',
halign='center',
valign='middle'
)
self.console_output.bind(size=self.console_output.setter('text_size'))
self.main_layout.add_widget(self.console_output)
def on_language_change(self, spinner, text):
self.active_lang = text
self.current_font = resolve_font_for_language(text)
self.lang_spinner.font_name = self.current_font
self.header_label.font_name = self.current_font
self.upload_btn.font_name = self.current_font
self.weather_label.font_name = self.current_font
self.console_output.font_name = self.current_font
self.header_label.text = translate_via_ml_kit("workspace_title", self.active_lang)
self.upload_btn.text = translate_via_ml_kit("upload_lbl", self.active_lang)
self.weather_label.text = translate_via_ml_kit("weather_lbl", self.active_lang)
if self.selected_file_path:
if self.weather_spinner.text in WEATHER_MAP:
self.execute_full_synthesis_pipeline(None, self.weather_spinner.text)
else:
self.process_layer1_and_2_matrices()
def open_file_chooser(self, instance):
request_android_storage_permissions()
default_path = '/storage/emulated/0' if os.path.exists('/storage/emulated/0') else os.path.expanduser('~')
content = BoxLayout(orientation='vertical')
chooser = SafeFileChooser(path=default_path, filters=['.jpg', '.jpeg', '*.png'])
content.add_widget(chooser)
select_btn = Button(text="Load Selected Image", font_name="Roboto", size_hint_y=0.15)
content.add_widget(select_btn)
popup = Popup(title="Select Soil Sample Photo", content=content, size_hint=(0.9, 0.9))
def on_select(btn):
if chooser.selection:
self.selected_file_path = str(next(iter(chooser.selection)))
popup.dismiss()
self.process_layer1_and_2_matrices()
select_btn.bind(on_press=on_select)
popup.open()
def process_layer1_and_2_matrices(self):
if not self.selected_file_path:
return
try:
ai_matrix, metrics, ch_a, ch_b = execute_layer1_construction_engine(self.selected_file_path)
except Exception as err:
self.console_output.font_name = "Roboto"
self.console_output.text = f"Could not load image:\n{err}"
return
self.cached_ai_matrix = ai_matrix
self.console_output.font_name = self.current_font
self.update_native_texture_view(self.img_ch_a, ch_a)
self.update_native_texture_view(self.img_ch_b, ch_b)
dark_pixel_ratio = np.sum(ai_matrix < 85) / ai_matrix.size
crystalline_check_mask = np.where(ai_matrix > 200, 255, 0).astype(np.uint8)
structural_variance = np.std(crystalline_check_mask)
self.soil_token = "CLAY" if dark_pixel_ratio > 0.45 else "SAND"
self.hazard_token = "SALT_OSMOTIC_HAZARD" if structural_variance > 28.0 else "SAFE"
l2_report = (
f"{translate_via_ml_kit('success_msg', self.active_lang)}\n"
f"- {translate_via_ml_kit('metric_res', self.active_lang)}: {metrics['original_resolution']}\n"
f"- {translate_via_ml_kit('metric_lux', self.active_lang)}: {metrics['mean_lightness']}\n"
f"- {translate_via_ml_kit('metric_shadow', self.active_lang)}: {metrics['shadow_detected']}\n\n"
f"{translate_via_ml_kit('clay_txt' if self.soil_token == 'CLAY' else 'sand_txt', self.active_lang)}\n"
f"{translate_via_ml_kit('crystalline_txt' if self.hazard_token == 'SALT_OSMOTIC_HAZARD' else 'amorphous_txt', self.active_lang)}"
)
self.console_output.text = l2_report
def execute_full_synthesis_pipeline(self, spinner, text):
if not hasattr(self, 'soil_token') or text not in WEATHER_MAP:
return
weather_token = WEATHER_MAP[text]
self.console_output.font_name = self.current_font
final_advice = f"{translate_via_ml_kit('result_hdr', self.active_lang)}\n\n"
if self.hazard_token == "SALT_OSMOTIC_HAZARD":
if weather_token == "W_RAINY":
final_advice += translate_via_ml_kit("salt_rain_alert", self.active_lang)
else:
final_advice += translate_via_ml_kit("salt_dry_alert", self.active_lang)
else:
if weather_token == "W_HOT":
final_advice += translate_via_ml_kit("clay_hot_txt" if self.soil_token == "CLAY" else "sand_hot_txt", self.active_lang)
elif weather_token == "W_RAINY":
final_advice += translate_via_ml_kit("clay_rain_txt" if self.soil_token == "CLAY" else "sand_rain_txt", self.active_lang)
elif weather_token == "W_COLD":
final_advice += translate_via_ml_kit("clay_cold_txt" if self.soil_token == "CLAY" else "sand_cold_txt", self.active_lang)
self.console_output.text = final_advice
def update_native_texture_view(self, ui_img_element, raw_gray_matrix):
h, w = raw_gray_matrix.shape
buf = np.flipud(raw_gray_matrix).tobytes()
texture = Texture.create(size=(w, h), colorfmt='luminance')
texture.blit_buffer(buf, colorfmt='luminance', bufferfmt='ubyte')
ui_img_element.texture = texture
if name == 'main':
AgriEdgeApp().run()
