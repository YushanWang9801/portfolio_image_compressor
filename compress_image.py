import os
import random
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageQt
import shutil
import io
import time
from pathlib import Path
import markdown
from datetime import datetime
import subprocess
import tempfile
import numpy as np

# 添加高效的压缩库
try:
    import pillow_avif  # 增加AVIF格式支持
    import pillow_heif  # 增加HEIF格式支持
except ImportError:
    pass


class ImageCompressorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("高保真图片压缩工具")
        self.root.geometry("1200x800")

        # 设置主题样式
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure(
            "TButton",
            padding=6,
            relief="flat",
            background="#4CAF50",
            foreground="white",
        )
        self.style.configure("TFrame", background="#F0F0F0")
        self.style.configure("TLabel", background="#F0F0F0", foreground="#333")
        self.style.configure("TProgressbar", thickness=20)

        # 初始化变量
        self.image_files = []
        self.current_image = None
        self.target_size_kb = 200
        self.output_folder = "output/download"
        self.compressed_folder = "output/compressed"
        self.report_data = []

        # 压缩算法参数
        self.compression_settings = {
            "jpeg": {"method": "smart", "min_quality": 20, "max_quality": 95},
            "png": {"method": "zopflipng", "max_colors": 256},
            "webp": {"method": "smart", "min_quality": 30, "max_quality": 90},
            "avif": {"method": "pillow", "quality": 70},
            "heic": {"method": "pyheif", "quality": 75},
        }

        # 支持的格式
        self.supported_formats = [
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".avif",
            ".heic",
            ".heif",
        ]

        # 创建UI
        self.create_widgets()

        # 自动加载图片
        self.load_image_files()
        self.show_random_image()

    def create_widgets(self):
        # 主容器
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 控制面板
        control_frame = ttk.LabelFrame(main_frame, text="控制面板", padding=10)
        control_frame.pack(fill=tk.X, pady=5)

        # 设置面板
        settings_frame = ttk.Frame(control_frame)
        settings_frame.pack(fill=tk.X, pady=5)

        ttk.Label(settings_frame, text="目标大小 (KB):").grid(row=0, column=0, padx=5)
        self.size_var = tk.StringVar(value=str(self.target_size_kb))
        size_entry = ttk.Entry(settings_frame, textvariable=self.size_var, width=8)
        size_entry.grid(row=0, column=1, padx=5)
        size_entry.bind("<Return>", self.update_target_size)

        ttk.Button(
            control_frame,
            text="选择图片文件夹",
            command=self.select_output_folder,
            width=15,
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            control_frame, text="随机选择图片", command=self.show_random_image, width=15
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            control_frame, text="压缩全部图片", command=self.compress_all, width=15
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            control_frame, text="生成报告", command=self.generate_report, width=15
        ).pack(side=tk.LEFT, padx=5)

        # 图片显示区域
        image_frame = ttk.LabelFrame(main_frame, text="图片预览", padding=10)
        image_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # 原图显示
        original_frame = ttk.LabelFrame(image_frame, text="原始图片")
        original_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.original_img_label = ttk.Label(original_frame)
        self.original_img_label.pack(pady=5)
        self.original_info = ttk.Label(
            original_frame, text="原图信息将显示在这里", wraplength=400
        )
        self.original_info.pack()

        # 分隔线
        ttk.Separator(image_frame, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=10
        )

        # 压缩图显示
        compressed_frame = ttk.LabelFrame(image_frame, text="压缩图片")
        compressed_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.compressed_img_label = ttk.Label(compressed_frame)
        self.compressed_img_label.pack(pady=5)
        self.compressed_info = ttk.Label(
            compressed_frame, text="压缩图信息将显示在这里", wraplength=400
        )
        self.compressed_info.pack()

        # 底部信息栏
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=5)

        ttk.Label(info_frame, text="支持的格式:").pack(side=tk.LEFT, padx=5)
        ttk.Label(
            info_frame, text=", ".join([fmt.upper() for fmt in self.supported_formats])
        ).pack(side=tk.LEFT, padx=5)

        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        ttk.Label(
            main_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=5,
        ).pack(fill=tk.X, padx=5, pady=5)

    def update_target_size(self, event):
        try:
            size = int(self.size_var.get())
            if size < 10 or size > 5000:
                raise ValueError
            self.target_size_kb = size
            if self.current_image:
                self.display_images()
            self.status_var.set(f"目标大小已更新: {self.target_size_kb}KB")
        except:
            self.size_var.set(str(self.target_size_kb))
            messagebox.showerror("错误", "请输入10-5000之间的有效数字")

    def select_output_folder(self):
        folder = filedialog.askdirectory(title="选择图片文件夹")
        if folder:
            self.output_folder = folder
            self.compressed_folder = os.path.join(os.path.dirname(folder), "compressed")
            self.load_image_files()
            self.show_random_image()
            self.status_var.set(f"已选择文件夹: {self.output_folder}")

    def load_image_files(self):
        self.image_files = []
        if os.path.exists(self.output_folder):
            for root, _, files in os.walk(self.output_folder):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in self.supported_formats:
                        full_path = os.path.join(root, file)
                        self.image_files.append(full_path)
            self.status_var.set(f"找到 {len(self.image_files)} 张图片")
        else:
            self.status_var.set("输出文件夹不存在")

    def show_random_image(self):
        if not self.image_files:
            messagebox.showwarning("警告", "没有找到可用的图片文件")
            return

        self.current_image = random.choice(self.image_files)
        self.display_images()

    def display_images(self):
        if not self.current_image:
            return

        try:
            # 显示原图
            original_img = Image.open(self.current_image)
            original_img.thumbnail((450, 450))
            original_tk = ImageTk.PhotoImage(original_img)
            self.original_img_label.configure(image=original_tk)
            self.original_img_label.image = original_tk

            # 显示原图信息
            file_size = os.path.getsize(self.current_image) / 1024
            width, height = original_img.size
            mode = original_img.mode
            self.original_info.config(
                text=f"文件: {os.path.basename(self.current_image)}\n"
                f"大小: {file_size:.1f}KB\n"
                f"尺寸: {width}x{height}\n"
                f"模式: {mode}\n"
                f"格式: {original_img.format}"
            )

            # 自动计算压缩并显示结果
            self.auto_compress_and_show(original_img)

        except Exception as e:
            messagebox.showerror("错误", f"无法加载图片: {str(e)}")

    def auto_compress_and_show(self, original_img):
        """自动计算压缩比例并显示结果"""
        try:
            start_time = time.time()

            # 调用优化后的压缩方法
            compressed_img, compression_data = self.compress_image(original_img.copy())

            # 显示压缩图
            compressed_img.thumbnail((450, 450))
            compressed_tk = ImageTk.PhotoImage(compressed_img)
            self.compressed_img_label.configure(image=compressed_tk)
            self.compressed_img_label.image = compressed_tk

            # 显示压缩信息
            if compression_data:
                info_text = (
                    f"压缩方法: {compression_data['method']}\n"
                    f"目标大小: {self.target_size_kb}KB\n"
                    f"实际大小: {compression_data['compressed_size']:.1f}KB\n"
                    f"压缩比: {compression_data['ratio']:.1%}\n"
                    f"处理时间: {compression_data['time']:.2f}秒"
                )
                if "quality" in compression_data:
                    info_text += f"\n质量参数: {compression_data['quality']}"
                if "colors" in compression_data:
                    info_text += f"\n使用颜色: {compression_data['colors']}"

                self.compressed_info.config(text=info_text)

        except Exception as e:
            messagebox.showerror("错误", f"压缩图片失败: {str(e)}")

    def compress_image(self, img):
        """优化后的图像压缩方法"""
        img_format = img.format.lower() if img.format else "jpeg"
        original_format = img_format
        file_ext = os.path.splitext(self.current_image)[1].lower()

        # 如果输入格式为HEIC/HEIF，转换格式处理
        if img_format in ["heic", "heif"] or file_ext in [".heic", ".heif"]:
            img_format = "jpeg"  # 转换为JPEG处理

        # 创建压缩数据字典
        compression_data = {
            "method": "Direct Copy",
            "compressed_size": os.path.getsize(self.current_image) / 1024,
            "quality": None,
            "colors": None,
            "time": 0.0,
            "ratio": 0.0,
            "format": img_format,
        }

        start_time = time.time()

        # 如果原始图片已经足够小，直接返回
        original_size_kb = compression_data["compressed_size"]
        if original_size_kb <= self.target_size_kb * 1.05:
            compression_data["method"] = "Direct Copy (Already Small)"
            compression_data["time"] = time.time() - start_time
            return img, compression_data

        # 根据不同格式使用不同的压缩方法
        if img_format in ["jpeg", "jpg"]:
            buffer = io.BytesIO()

            # 高质量模式优先尝试
            quality = 90
            img.save(
                buffer, format="JPEG", quality=quality, optimize=True, progressive=True
            )
            compressed_size = len(buffer.getvalue()) / 1024

            # 如果高质量模式已经满足需求
            if compressed_size <= self.target_size_kb:
                compression_data["method"] = "High Quality JPEG"
                compression_data["quality"] = quality
                compression_data["compressed_size"] = compressed_size
                compression_data["ratio"] = 1 - compressed_size / original_size_kb
                compression_data["time"] = time.time() - start_time
                return Image.open(buffer), compression_data

            # 执行智能压缩
            compressed_img, quality = self.smart_jpeg_compress(img, self.target_size_kb)
            compression_data["method"] = "Smart JPEG Compression"
            compression_data["quality"] = quality
            compression_data["time"] = time.time() - start_time

            # 计算压缩后大小
            buffer = io.BytesIO()
            compressed_img.save(
                buffer, format="JPEG", quality=quality, optimize=True, progressive=True
            )
            compressed_size = len(buffer.getvalue()) / 1024
            compression_data["compressed_size"] = compressed_size
            compression_data["ratio"] = 1 - compressed_size / original_size_kb
            compression_data["format"] = "jpeg"

            return compressed_img, compression_data

        elif img_format == "png":
            # 尝试使用高级PNG压缩
            compressed_img, method = self.compress_png(img, self.target_size_kb)

            compression_data["method"] = method
            compression_data["time"] = time.time() - start_time

            # 计算压缩后大小
            buffer = io.BytesIO()
            compressed_img.save(buffer, format="PNG", optimize=True)
            compressed_size = len(buffer.getvalue()) / 1024
            compression_data["compressed_size"] = compressed_size
            compression_data["ratio"] = 1 - compressed_size / original_size_kb
            compression_data["format"] = "png"

            return compressed_img, compression_data

        elif img_format == "webp":
            # WebP压缩
            compressed_img, quality = self.smart_webp_compress(img, self.target_size_kb)

            compression_data["method"] = "Smart WebP Compression"
            compression_data["quality"] = quality
            compression_data["time"] = time.time() - start_time

            # 计算压缩后大小
            buffer = io.BytesIO()
            compressed_img.save(buffer, format="WEBP", quality=quality, method=6)
            compressed_size = len(buffer.getvalue()) / 1024
            compression_data["compressed_size"] = compressed_size
            compression_data["ratio"] = 1 - compressed_size / original_size_kb
            compression_data["format"] = "webp"

            return compressed_img, compression_data

        else:
            # 其他格式尝试转为WebP或高质量JPEG
            try:
                # 尝试转换为WebP
                compressed_img, quality = self.smart_webp_compress(
                    img, self.target_size_kb
                )

                compression_data["method"] = "Convert to WebP"
                compression_data["quality"] = quality
                compression_data["time"] = time.time() - start_time
                compression_data["format"] = "webp"

                buffer = io.BytesIO()
                compressed_img.save(buffer, format="WEBP", quality=quality, method=6)
                compressed_size = len(buffer.getvalue()) / 1024
                compression_data["compressed_size"] = compressed_size
                compression_data["ratio"] = 1 - compressed_size / original_size_kb

                return compressed_img, compression_data
            except:
                # 如果WebP转换失败，回退到JPEG压缩
                compressed_img, quality = self.smart_jpeg_compress(
                    img, self.target_size_kb
                )

                compression_data["method"] = f"Convert to JPEG (from {original_format})"
                compression_data["quality"] = quality
                compression_data["time"] = time.time() - start_time
                compression_data["format"] = "jpeg"

                buffer = io.BytesIO()
                compressed_img.save(
                    buffer,
                    format="JPEG",
                    quality=quality,
                    optimize=True,
                    progressive=True,
                )
                compressed_size = len(buffer.getvalue()) / 1024
                compression_data["compressed_size"] = compressed_size
                compression_data["ratio"] = 1 - compressed_size / original_size_kb

                return compressed_img, compression_data

    def smart_jpeg_compress(self, img, target_kb):
        """智能JPEG压缩，优先保留高质量"""

        # 使用Pillow的高质量保存
        def save_jpeg(quality):
            buffer = io.BytesIO()
            img.save(
                buffer, format="JPEG", quality=quality, optimize=True, progressive=True
            )
            return buffer.getvalue()

        # 高质量优先策略
        low, high = 40, 95
        best_quality = high
        best_data = save_jpeg(best_quality)
        best_size = len(best_data) / 1024

        # 如果高质量已经小于目标大小，直接返回
        if best_size <= target_kb:
            return Image.open(io.BytesIO(best_data)), best_quality

        # 二分法查找最佳质量
        while low <= high:
            mid = (low + high) // 2
            mid_data = save_jpeg(mid)
            mid_size = len(mid_data) / 1024

            if mid_size < target_kb:
                best_quality = mid
                best_data = mid_data
                best_size = mid_size
                low = mid + 1
            else:
                high = mid - 1

        # 确保不会低于最低质量
        if best_quality < 50 and best_size > target_kb:
            quality = max(10, best_quality - 5)
            return self.smart_jpeg_compress(img, target_kb)

        return Image.open(io.BytesIO(best_data)), best_quality

    def compress_png(self, img, target_kb):
        """高级PNG压缩方法"""
        # 1. 尝试无损压缩
        try:
            compressed_img = self.compress_png_lossless(img)
            buffer = io.BytesIO()
            compressed_img.save(buffer, format="PNG", optimize=True)
            compressed_size = len(buffer.getvalue()) / 1024

            if compressed_size <= target_kb:
                return compressed_img, "PNG Lossless (Zopfli)"
        except Exception as e:
            print(f"PNG无损压缩失败: {e}")

        # 2. 尝试有损压缩（减少颜色）
        try:
            compressed_img = self.compress_png_lossy(img, 256)  # 256色
            buffer = io.BytesIO()
            compressed_img.save(buffer, format="PNG", optimize=True)
            compressed_size = len(buffer.getvalue()) / 1024

            if compressed_size <= target_kb:
                return compressed_img, "PNG Lossy (256 colors)"
        except Exception as e:
            print(f"PNG有损压缩失败: {e}")

        # 3. 降为128色
        try:
            compressed_img = self.compress_png_lossy(img, 128)
            buffer = io.BytesIO()
            compressed_img.save(buffer, format="PNG", optimize=True)
            compressed_size = len(buffer.getvalue()) / 1024

            if compressed_size <= target_kb:
                return compressed_img, "PNG Lossy (128 colors)"
        except Exception as e:
            print(f"PNG有损压缩失败: {e}")

        # 4. 最终转为WebP
        webp_img, quality = self.smart_webp_compress(img, target_kb)
        return webp_img, f"Convert to WebP (quality={quality})"

    def compress_png_lossless(self, img):
        """使用Zopfli进行无损PNG压缩（需要安装optipng或zopflipng）"""
        try:
            # 使用系统optipng命令
            temp_input = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            temp_output = tempfile.NamedTemporaryFile(suffix=".png", delete=False)

            img.save(temp_input, format="PNG")
            temp_input.close()

            # 使用高级压缩参数
            cmd = [
                "optipng",
                "-o6",
                "-quiet",
                temp_input.name,
                "-out",
                temp_output.name,
            ]
            subprocess.run(
                cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

            compressed_img = Image.open(temp_output.name)

            # 清理临时文件
            os.unlink(temp_input.name)
            os.unlink(temp_output.name)

            return compressed_img
        except:
            # 如果optipng不可用，使用Pillow的最佳优化
            buffer = io.BytesIO()
            img.save(buffer, format="PNG", compress_level=9)
            return Image.open(buffer)

    def compress_png_lossy(self, img, max_colors):
        """有损PNG压缩 - 减少颜色数量"""
        # 转换为P模式（调色板模式）
        if img.mode == "RGBA":
            # 处理透明通道
            alpha = img.split()[-1]
            img = img.convert("RGB")

        # 转换时使用高保真方法
        palette_img = img.quantize(colors=max_colors, method=Image.MEDIANCUT)

        # 转换回RGBA如果原始有透明通道
        if img.mode == "RGBA":
            palette_img = palette_img.convert("RGBA")
            palette_img.putalpha(alpha)

        return palette_img

    def smart_webp_compress(self, img, target_kb):
        """智能WebP压缩"""

        def save_webp(quality):
            buffer = io.BytesIO()
            img.save(buffer, format="WEBP", quality=quality, method=6)
            return buffer.getvalue()

        # 高质量优先策略
        low, high = 40, 90
        best_quality = high
        best_data = save_webp(best_quality)
        best_size = len(best_data) / 1024

        # 如果高质量已经小于目标大小，直接返回
        if best_size <= target_kb:
            return Image.open(io.BytesIO(best_data)), best_quality

        # 二分法查找最佳质量
        while low <= high:
            mid = (low + high) // 2
            mid_data = save_webp(mid)
            mid_size = len(mid_data) / 1024

            if mid_size < target_kb:
                best_quality = mid
                best_data = mid_data
                best_size = mid_size
                low = mid + 1
            else:
                high = mid - 1

        return Image.open(io.BytesIO(best_data)), best_quality

    def compress_all(self):
        if not self.image_files:
            messagebox.showwarning("警告", "没有找到可用的图片文件")
            return

        # 创建压缩文件夹
        if os.path.exists(self.compressed_folder):
            shutil.rmtree(self.compressed_folder)
        os.makedirs(self.compressed_folder)

        # 初始化报告数据
        self.report_data = []
        total = len(self.image_files)
        processed = 0
        skipped = 0

        # 在主窗口显示压缩状态
        self.status_var.set(f"正在压缩: 0/{total} (跳过:0)")

        # 创建进度窗口
        progress_window = tk.Toplevel(self.root)
        progress_window.title("压缩进度")
        progress_window.geometry("500x200")

        progress_label = ttk.Label(
            progress_window, text="压缩处理中...", font=("Arial", 12)
        )
        progress_label.pack(pady=10)

        current_file_label = ttk.Label(progress_window, text="当前文件: ")
        current_file_label.pack(pady=5)

        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(
            progress_window, variable=progress_var, maximum=total, length=450
        )
        progress_bar.pack(pady=10)

        status_label = ttk.Label(progress_window, text="状态: 初始化...")
        status_label.pack(pady=5)

        cancel_button = ttk.Button(
            progress_window,
            text="取消",
            command=lambda: setattr(self, "cancel_flag", True),
        )
        cancel_button.pack(pady=10)

        self.cancel_flag = False
        progress_window.grab_set()
        self.root.update()

        start_time = time.time()

        for img_path in self.image_files:
            if self.cancel_flag:
                status_label.config(text="操作已取消")
                time.sleep(1)
                progress_window.destroy()
                self.status_var.set("用户取消压缩")
                return

            processed += 1
            self.status_var.set(f"正在压缩: {processed}/{total} (跳过:{skipped})")
            current_file_label.config(text=f"当前文件: {os.path.basename(img_path)}")
            status_label.config(text="正在处理...")
            progress_var.set(processed)
            progress_window.update()

            # 获取相对路径
            rel_path = os.path.relpath(img_path, self.output_folder)
            dest_path = os.path.join(self.compressed_folder, rel_path)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            # 获取原始大小
            original_size = os.path.getsize(img_path) / 1024

            # 如果小于目标大小，直接复制
            if original_size <= self.target_size_kb * 1.05:
                shutil.copy2(img_path, dest_path)
                skipped += 1
                self.report_data.append(
                    {
                        "file": img_path,
                        "original_size": original_size,
                        "compressed_size": original_size,
                        "status": "skipped (already small enough)",
                        "method": "direct copy",
                        "destination": dest_path,
                    }
                )
                continue

            try:
                img = Image.open(img_path)
                file_format = img.format.lower() if img.format else ""

                # 调用压缩方法
                compressed_img, compression_data = self.compress_image(img)

                # 获取实际压缩大小
                buffer = io.BytesIO()
                compressed_img.save(
                    buffer,
                    format=(
                        "JPEG"
                        if compression_data["format"] == "jpeg"
                        else "PNG" if compression_data["format"] == "png" else "WEBP"
                    ),
                )
                compressed_size = len(buffer.getvalue()) / 1024

                # 保存图片，保留EXIF信息
                compressed_img.save(
                    dest_path,
                    quality=compression_data.get("quality", 85),
                    optimize=True,
                )

                # 报告数据
                report_item = {
                    "file": img_path,
                    "original_size": original_size,
                    "compressed_size": compressed_size,
                    "method": compression_data.get("method", "unknown"),
                    "quality": compression_data.get("quality", None),
                    "colors": compression_data.get("colors", None),
                    "status": "success",
                    "ratio": 1 - (compressed_size / original_size),
                    "destination": dest_path,
                }

                self.report_data.append(report_item)

                status_label.config(
                    text=f"完成: 大小 {compressed_size:.1f}KB (原 {original_size:.1f}KB)"
                )

            except Exception as e:
                # 压缩失败时复制原图
                shutil.copy2(img_path, dest_path)
                self.report_data.append(
                    {
                        "file": img_path,
                        "original_size": original_size,
                        "compressed_size": original_size,
                        "status": f"failed: {str(e)}",
                        "method": "copy",
                        "destination": dest_path,
                    }
                )
                status_label.config(text=f"失败: {str(e)}")

        progress_window.destroy()

        elapsed = time.time() - start_time
        success_count = len([x for x in self.report_data if x["status"] == "success"])

        messagebox.showinfo(
            "完成",
            f"图片压缩完成!\n\n"
            f"处理总数: {total}\n"
            f"成功压缩: {success_count}\n"
            f"跳过(已足够小): {skipped}\n"
            f"耗时: {elapsed:.1f}秒\n"
            f"平均耗时: {elapsed/total if total else 0:.2f}秒/图片",
        )
        self.status_var.set(f"压缩完成! 结果保存在: {self.compressed_folder}")

    def generate_report(self):
        if not self.report_data:
            messagebox.showwarning("警告", "没有可用的压缩数据，请先执行压缩")
            return

        # 创建Markdown报告
        report = f"# 智能图片压缩报告\n\n"
        report += f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"**目标大小**: {self.target_size_kb} KB\n"
        report += f"**源文件夹**: {self.output_folder}\n"
        report += f"**目标文件夹**: {self.compressed_folder}\n\n"

        report += "## 统计摘要\n\n"

        # 分类统计压缩方法
        method_stats = {}
        for item in self.report_data:
            method = item.get("method", "unknown")
            if method not in method_stats:
                method_stats[method] = {"count": 0, "saved": 0}
            method_stats[method]["count"] += 1
            method_stats[method]["saved"] += (
                item["original_size"] - item["compressed_size"]
            )

        total_saved = sum(
            item["original_size"] - item["compressed_size"] for item in self.report_data
        )
        avg_ratio = (
            total_saved / sum(item["original_size"] for item in self.report_data)
            if self.report_data
            else 0
        )

        report += f"- 总文件数: {len(self.report_data)}\n"
        report += f"- 总压缩节省: {total_saved:.1f} KB\n"
        report += f"- 平均压缩率: {avg_ratio:.1%}\n"
        report += f"- 压缩方法分布:\n"

        for method, stats in method_stats.items():
            report += (
                f"  - {method}: {stats['count']} 文件 (节省 {stats['saved']:.1f}KB)\n"
            )

        report += "\n## 文件处理详情\n\n"
        report += "| 原文件 | 原始大小(KB) | 压缩后大小(KB) | 压缩率 | 方法 | 状态 |\n"
        report += "|--------|-------------|----------------|--------|------|------|\n"

        for item in self.report_data:
            ratio = 1 - (item["compressed_size"] / item["original_size"])
            report += (
                f"| {os.path.basename(item['file'])} | {item['original_size']:.1f} | "
                f"{item['compressed_size']:.1f} | {ratio:.1%} | "
                f"{item.get('method', '')} | {item['status']} |\n"
            )

        # 保存报告
        report_folder = os.path.join(os.path.dirname(self.compressed_folder), "reports")
        os.makedirs(report_folder, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(report_folder, f"compression_report_{timestamp}.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        # 转换为HTML
        html = markdown.markdown(report)
        html_path = os.path.join(report_folder, f"compression_report_{timestamp}.html")

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(
                f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>图片压缩报告</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; max-width: 1200px; margin: 0 auto; padding: 20px; }}
                    table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    .summary {{ background-color: #f8f8f8; padding: 15px; border-radius: 5px; }}
                    .chart-container {{ width: 100%; height: 300px; }}
                </style>
            </head>
            <body>
            {html}
            </body>
            </html>
            """
            )

        # 显示报告生成成功的消息
        show_in_folder = messagebox.askyesno(
            "报告生成成功",
            f"Markdown和HTML报告已生成:\n\n"
            f"{report_path}\n"
            f"{html_path}\n\n"
            "是否在资源管理器中打开报告文件夹?",
        )

        if show_in_folder:
            if os.name == "nt":
                os.startfile(report_folder)
            elif os.name == "posix":
                subprocess.run(
                    ["open", report_folder]
                    if sys.platform == "darwin"
                    else ["xdg-open", report_folder]
                )

        self.status_var.set(f"报告已生成: {report_path}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageCompressorApp(root)
    root.mainloop()
