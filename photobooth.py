import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk, ImageDraw, ImageFont
import cv2
import requests
import os
import numpy as np

class PhotoBoothApp:
    def __init__(self, window, window_title):
        self.window = window
        self.window.title(window_title)
        self.window.geometry("1000x700")
        self.window.configure(bg="#f0f0f0")

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TButton", padding=10, font=("Arial", 12))
        self.style.configure("TLabel", background="#f0f0f0", font=("Arial", 12))
        self.style.configure("Selected.TButton", padding=10, font=("Arial", 12), borderwidth=5, relief="solid")

        self.video_source = 0
        self.vid = None
        
        self.photos = []
        self.selected_photos = []
        
        self.frame_colors = [
            ("#000000", "Black"),
            ("#FFFFFF", "White"),
            ("#FF0000", "Red"),
            ("#00FF00", "Green"),
            ("#0000FF", "Blue"),
            ("#FFFF00", "Yellow"),
            ("#FF00FF", "Magenta"),
            ("#00FFFF", "Cyan")
        ]
        self.frame_color = self.frame_colors[0][0]  # Default to black
        self.frame_sets = None

        self.download_anton_font()
        self.create_frame_selection_page()

    def download_anton_font(self):
        font_url = "https://github.com/google/fonts/raw/main/ofl/anton/Anton-Regular.ttf"
        font_path = "Anton-Regular.ttf"
        if not os.path.exists(font_path):
            response = requests.get(font_url)
            with open(font_path, "wb") as f:
                f.write(response.content)

    def clear_window(self):
        for widget in self.window.winfo_children():
            widget.destroy()

    def create_frame_selection_page(self):
        self.clear_window()
        
        title_label = ttk.Label(self.window, text="Select a Frame Set", font=("Arial", 16, "bold"))
        title_label.pack(pady=20)

        frame_folder = "frames"
        if not os.path.exists(frame_folder):
            os.makedirs(frame_folder)
            messagebox.showinfo("Info", f"Created '{frame_folder}' directory. Please add frame set folders to this directory.")
            return

        frame_sets = [f for f in os.listdir(frame_folder) if os.path.isdir(os.path.join(frame_folder, f))]
        
        frame_container = ttk.Frame(self.window)
        frame_container.pack(expand=True, fill=tk.BOTH)

        # No Frame button
        no_frame_path = os.path.join(frame_folder, "noframe.png")
        if os.path.exists(no_frame_path):
            img = Image.open(no_frame_path)
            img.thumbnail((200, 200))
            photo = ImageTk.PhotoImage(img)
            btn = ttk.Button(frame_container, image=photo, text="No Frame", compound=tk.TOP,
                             command=lambda: self.set_frame_set(None))
            btn.image = photo
            btn.grid(row=0, column=0, padx=10, pady=10)

        for i, frame_set in enumerate(frame_sets, start=1):
            frame_set_path = os.path.join(frame_folder, frame_set)
            icon_path = os.path.join(frame_set_path, "icon.png")
            if os.path.exists(icon_path):
                img = Image.open(icon_path)
                img.thumbnail((200, 200))
                photo = ImageTk.PhotoImage(img)
                
                btn = ttk.Button(frame_container, image=photo, text=frame_set, compound=tk.TOP,
                                 command=lambda fs=frame_set: self.set_frame_set(fs))
                btn.image = photo
                btn.grid(row=i//4, column=i%4, padx=10, pady=10)

        next_button = ttk.Button(self.window, text="Next", command=self.create_photo_capture_page)
        next_button.pack(pady=20)

    def set_frame_set(self, frame_set):
        if frame_set is None:
            self.frame_sets = None
            messagebox.showinfo("Info", "No frame selected.")
        else:
            frame_set_path = os.path.join("frames", frame_set)
            frames = [f for f in os.listdir(frame_set_path) if f.lower().endswith(('.png', '.jpg', '.jpeg')) and f != "icon.png"]
            self.frame_sets = [Image.open(os.path.join(frame_set_path, f)).convert('RGBA') for f in sorted(frames)[:4]]
            messagebox.showinfo("Info", f"Frame set '{frame_set}' selected.")

    def create_photo_capture_page(self):
        self.clear_window()
        
        title_label = ttk.Label(self.window, text="Take Photos", font=("Arial", 16, "bold"))
        title_label.pack(pady=20)

        self.canvas = tk.Canvas(self.window, width=640, height=480, bg="black", highlightthickness=0)
        self.canvas.pack()

        button_frame = ttk.Frame(self.window)
        button_frame.pack(pady=20)

        self.btn_snapshot = ttk.Button(button_frame, text="Take Picture", command=self.snapshot)
        self.btn_snapshot.pack(side=tk.LEFT, padx=10)

        self.photo_count_label = ttk.Label(button_frame, text="Photos: 0/8")
        self.photo_count_label.pack(side=tk.LEFT, padx=10)

        self.timer_label = ttk.Label(button_frame, text="")
        self.timer_label.pack(side=tk.LEFT, padx=10)

        self.vid = cv2.VideoCapture(self.video_source)
        self.update()
        self.start_timer()

    def start_timer(self):
        self.countdown(5)

    def countdown(self, count):
        if count > 0 and len(self.photos) < 8:
            self.timer_label.config(text=f"Next photo in: {count}")
            self.window.after(1000, self.countdown, count - 1)
        elif len(self.photos) < 8:
            self.snapshot()

    def snapshot(self):
        ret, frame = self.vid.read()
        if ret:
            frame = cv2.flip(frame, 1)  # Mirror the image
            photo = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            
            if self.frame_sets:
                frame_index = (len(self.photos) // 2) % 4  # Take each frame twice
                photo = Image.alpha_composite(photo.convert('RGBA'), self.frame_sets[frame_index].resize(photo.size))
            
            self.photos.append(photo)
            
            # Flash effect
            self.canvas.config(bg="white")
            self.window.after(100, lambda: self.canvas.config(bg="black"))
            
            self.photo_count_label.config(text=f"Photos: {len(self.photos)}/8")
            
            if len(self.photos) >= 8:
                self.vid.release()
                self.create_photo_selection_page()
            else:
                self.start_timer()

    def update(self):
        ret, frame = self.vid.read()
        if ret:
            frame = cv2.flip(frame, 1)  # Mirror the image
            
            # Overlay frame if selected
            if self.frame_sets:
                frame_index = (len(self.photos) // 2) % 4  # Show each frame twice
                frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA))
                overlay = self.frame_sets[frame_index].resize(frame_pil.size)
                frame_with_overlay = Image.alpha_composite(frame_pil, overlay)
                frame = cv2.cvtColor(np.array(frame_with_overlay), cv2.COLOR_RGBA2BGR)
            
            self.photo = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
            self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
        
        if len(self.photos) < 8:
            self.window.after(15, self.update)

    def create_photo_selection_page(self):
        self.clear_window()

        title_label = ttk.Label(self.window, text="Select Photos and Color", font=("Arial", 16, "bold"))
        title_label.pack(pady=20)

        main_frame = ttk.Frame(self.window)
        main_frame.pack(expand=True, fill=tk.BOTH)

        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, padx=20, pady=20, expand=True, fill=tk.BOTH)

        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, padx=20, pady=20)

        self.photo_frame = ttk.Frame(left_frame)
        self.photo_frame.pack(pady=10)

        self.photo_buttons = []
        for i, photo in enumerate(self.photos):
            img = ImageTk.PhotoImage(photo.resize((150, 112), Image.LANCZOS))
            btn = ttk.Button(self.photo_frame, image=img, command=lambda idx=i: self.toggle_selection(idx))
            btn.image = img
            btn.grid(row=i//4, column=i%4, padx=5, pady=5)
            self.photo_buttons.append(btn)

        color_frame = ttk.Frame(left_frame)
        color_frame.pack(pady=20)

        ttk.Label(color_frame, text="Frame Color:").pack(side=tk.LEFT, padx=5)
        for color, name in self.frame_colors:
            btn = tk.Button(color_frame, bg=color, width=2, height=1, command=lambda c=color: self.set_color(c))
            btn.pack(side=tk.LEFT, padx=2)

        self.preview_canvas = tk.Canvas(right_frame, width=300, height=450, bg="white", highlightthickness=1)
        self.preview_canvas.pack(pady=10)

        self.btn_create_strip = ttk.Button(right_frame, text="Create Photo Strip", command=self.create_strip)
        self.btn_create_strip.pack(pady=10)

        self.update_preview()

    def toggle_selection(self, index):
        if index in self.selected_photos:
            self.selected_photos.remove(index)
        elif len(self.selected_photos) < 4:
            self.selected_photos.append(index)
        self.update_preview()
        self.update_photo_buttons()

    def update_photo_buttons(self):
        for i, btn in enumerate(self.photo_buttons):
            if i in self.selected_photos:
                btn.config(style="Selected.TButton")
            else:
                btn.config(style="TButton")

    def set_color(self, color):
        self.frame_color = color
        self.update_preview()

    def update_preview(self):
        if len(self.selected_photos) > 0:
            strip = self.create_photo_strip(preview=True)
            photo = ImageTk.PhotoImage(strip)
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(0, 0, anchor=tk.NW, image=photo)
            self.preview_canvas.image = photo

    def create_strip(self):
        if len(self.selected_photos) != 4:
            messagebox.showwarning("Warning", "Please select exactly 4 pictures.")
            return

        strip = self.create_photo_strip()
        strip.save("photo_strip.png", 'PNG')
        messagebox.showinfo("Success", "Photo strip saved as photo_strip.png")
        self.window.quit()

    def create_photo_strip(self, preview=False):
        strip_width = 2 * 300  # 2 inches at 300 DPI
        strip_height = 6 * 300  # 6 inches at 300 DPI
        
        photo_strip = Image.new('RGB', (strip_width, strip_height), color=self.frame_color)
        draw = ImageDraw.Draw(photo_strip)

        top_margin = 30
        side_margin = 30
        bottom_margin = 150
        photo_interval = 30

        photo_width = strip_width - 2 * side_margin
        total_photo_height = strip_height - top_margin - bottom_margin - 3 * photo_interval
        photo_height = total_photo_height // 4

        for i, idx in enumerate(self.selected_photos):
            y = top_margin + i * (photo_height + photo_interval)
            
            pic = self.photos[idx].resize((photo_width, photo_height), Image.LANCZOS)
            photo_strip.paste(pic, (side_margin, y))

        try:
            font = ImageFont.truetype("Anton-Regular.ttf", 72)
        except IOError:
            font = ImageFont.load_default()
        
        watermark_y = strip_height - bottom_margin // 2
        draw.text((strip_width // 2, watermark_y), "LEAN4CUT", 
                  fill='white', font=font, anchor="ms", stroke_width=3, stroke_fill='black')

        if preview:
            photo_strip.thumbnail((300, 450))

        return photo_strip

if __name__ == "__main__":
    root = tk.Tk()
    app = PhotoBoothApp(root, "MELA4CUT Photo Booth")
    root.mainloop()
