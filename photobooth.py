import tkinter as tk
import datetime
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk, ImageDraw, ImageFont
import cv2
import requests
import os
import numpy as np
import time
import qrcode

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
        
        self.frame_order = [0, 0, 1, 1, 2, 2, 3, 3]  # Frame order: 1 1 2 2 3 3 4 4

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

        self.is_taking_photo = False
        self.timer_running = False
        self.flash_duration = 500  # milliseconds
        self.timer_id = None  # To store the timer event ID

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

    def set_frame_set(self, frame_set):
        if frame_set is None:
            self.frame_sets = None
        else:
            frame_set_path = os.path.join("frames", frame_set)
            frames = [f for f in os.listdir(frame_set_path) if f.lower().endswith(('.png', '.jpg', '.jpeg')) and f != "icon.png"]
            self.frame_sets = [Image.open(os.path.join(frame_set_path, f)).convert('RGBA') for f in sorted(frames)[:4]]
        
        self.create_photo_capture_page()

    def create_photo_capture_page(self):
        self.clear_window()
        
        title_label = ttk.Label(self.window, text="Take Photos", font=("Arial", 16, "bold"))
        title_label.pack(pady=20)

        self.canvas = tk.Canvas(self.window, width=640, height=480, bg="black", highlightthickness=0)
        self.canvas.pack()

        button_frame = ttk.Frame(self.window)
        button_frame.pack(pady=20)

        self.btn_snapshot = ttk.Button(button_frame, text="Take Picture", command=self.manual_snapshot)
        self.btn_snapshot.pack(side=tk.LEFT, padx=10)

        self.photo_count_label = ttk.Label(button_frame, text="Photos: 1/8")
        self.photo_count_label.pack(side=tk.LEFT, padx=10)

        self.timer_label = ttk.Label(button_frame, text="")
        self.timer_label.pack(side=tk.LEFT, padx=10)

        self.vid = cv2.VideoCapture(self.video_source)
        self.update()
        self.start_timer()

    def start_timer(self):
        if not self.timer_running and len(self.photos) < 8:
            self.timer_running = True
            self.countdown(4)

    def countdown(self, count):
        if self.timer_id:  # Cancel any existing timer
            self.window.after_cancel(self.timer_id)
        
        if count > 0 and len(self.photos) < 8 and self.timer_running:
            self.timer_label.config(text=f"Next photo in: {count}")
            self.timer_id = self.window.after(1000, self.countdown, count - 1)
        elif len(self.photos) < 8 and self.timer_running:
            self.auto_snapshot()

    def manual_snapshot(self):
        if not self.is_taking_photo:
            self.is_taking_photo = True
            self.timer_running = False
            if self.timer_id:
                self.window.after_cancel(self.timer_id)
            self.timer_label.config(text="")
            self.take_photo()

    def auto_snapshot(self):
        if not self.is_taking_photo:
            self.is_taking_photo = True
            self.take_photo()

    def take_photo(self):
        ret, frame = self.vid.read()
        if ret:
            frame = cv2.flip(frame, 1)  # Mirror the image
            photo = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            
            # Resize photo to maintain aspect ratio
            target_size = (600, 400)  # 2:3 aspect ratio
            photo.thumbnail(target_size, Image.LANCZOS)
            
            if self.frame_sets:
                frame_index = self.frame_order[len(self.photos)]
                frame_image = self.frame_sets[frame_index].resize(photo.size, Image.LANCZOS)
                photo = Image.alpha_composite(photo.convert('RGBA'), frame_image)
            
            self.photos.append(photo)
            
            # Flash effect
            self.canvas.config(bg="white")
            self.window.after(self.flash_duration, self.end_photo_capture)

    def end_photo_capture(self):
        self.canvas.config(bg="black")
        self.photo_count_label.config(text=f"Photo: {len(self.photos)+1}/8")
        
        if len(self.photos) >= 8:
            self.vid.release()
            self.create_photo_selection_page()
        else:
            self.is_taking_photo = False
            self.timer_running = False
            self.start_timer()

    def update(self):
        ret, frame = self.vid.read()
        if ret:
            frame = cv2.flip(frame, 1)  # Mirror the image
            
            # Resize frame to maintain aspect ratio
            height, width = frame.shape[:2]
            target_width = 640
            target_height = int(target_width * height / width)
            frame = cv2.resize(frame, (target_width, target_height))
            
            # Overlay frame if selected
            if self.frame_sets:
                frame_index = self.frame_order[len(self.photos)]
                frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA))
                overlay = self.frame_sets[frame_index].resize(frame_pil.size, Image.LANCZOS)
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
    
    # Get the current date and time
        now = datetime.datetime.now()
    
    # Create a new folder for the result
        result_folder = os.path.join(os.getcwd(), 'result')
        if not os.path.exists(result_folder):
            os.mkdir(result_folder)
    
    # Save each photo as a PNG file with the current date and time
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        strip = self.create_photo_strip()
        strip.save(os.path.join(result_folder, f'{timestamp}.png'), 'PNG')
    
    # Display a message box with the success of the operation
        messagebox.showinfo("Success", "Photos saved as PNG files in the result folder.")
        self.show_qr_code_page(os.path.join(result_folder, f'{timestamp}.png'))

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
            
            pic = self.photos[idx].copy()
            pic.thumbnail((photo_width, photo_height), Image.LANCZOS)
            
            # Calculate position to center the photo
            x_offset = (photo_width - pic.width) // 2 + side_margin
            y_offset = y + (photo_height - pic.height) // 2
            
            photo_strip.paste(pic, (x_offset, y_offset))

        try:
            font = ImageFont.truetype("Anton-Regular.ttf", 72)
        except IOError:
            font = ImageFont.load_default()
        
        watermark_y = strip_height - bottom_margin // 2
        draw.text((strip_width // 2, watermark_y), "LEAN4CUT", 
                  fill='white', font=font, anchor="ms", stroke_width=3, stroke_fill='black')

        if preview:
            photo_strip.thumbnail((300, 450), Image.LANCZOS)

        return photo_strip

    def show_qr_code_page(self, file_path):
        self.clear_window()  # Clear the existing window content

    # Generate the QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(file_path)
        qr.make(fit=True)
    
        qr_img = qr.make_image(fill='black', back_color='white')
        qr_img = qr_img.resize((300, 300), Image.LANCZOS)  # Use Image.LANCZOS here
        qr_photo = ImageTk.PhotoImage(qr_img)

    # Create a label to display the QR code
        qr_label = ttk.Label(self.window, image=qr_photo)
        qr_label.image = qr_photo  # Keep a reference to avoid garbage collection
        qr_label.pack(pady=20)

    # Add a label with instructions
        instructions = ttk.Label(self.window, text="Scan this QR code to download your photo strip.")
        instructions.pack(pady=20)

    # Add a button to return to the main page
        back_button = ttk.Button(self.window, text="Back to Main Page", command=self.restart_program)
        back_button.pack(pady=20)

    def clear_window(self):
        for widget in self.window.winfo_children():
            widget.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = PhotoBoothApp(root, "LEAN4CUT Photo Booth")
    root.mainloop()