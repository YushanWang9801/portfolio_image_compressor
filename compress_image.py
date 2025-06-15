import os
import random
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import shutil
import io
import time
from pathlib import Path
import markdown
from datetime import datetime


class ImageCompressorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("智能图片压缩工具")
        self.root.geometry("1000x700")

        # 初始化变量
        self.image_files = []
        self.current_image = None
        self.target_size_kb = 200
        self.output_folder = "output/download"
        self.compressed_folder = "output/compressed"
        self.report_data = []

        # 创建UI
        self.create_widgets()

        # 自动加载图片
        self.load_image_files()
        self.show_random_image()

    def create_widgets(self):
        # 控制面板
        control_frame = ttk.Frame(self.root, padding=10)
        control_frame.pack(fill=tk.X)

        ttk.Button(
            control_frame, text="选择图片文件夹", command=self.select_output_folder
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            control_frame, text="随机选择图片", command=self.show_random_image
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="压缩全部图片", command=self.compress_all).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(control_frame, text="生成报告", command=self.generate_report).pack(
            side=tk.LEFT, padx=5
        )

        # 图片显示区域
        image_frame = ttk.Frame(self.root)
        image_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 原图显示
        original_frame = ttk.Frame(image_frame)
        original_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
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
        compressed_frame = ttk.Frame(image_frame)
        compressed_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.compressed_img_label = ttk.Label(compressed_frame)
        self.compressed_img_label.pack(pady=5)
        self.compressed_info = ttk.Label(
            compressed_frame, text="压缩图信息将显示在这里", wraplength=400
        )
        self.compressed_info.pack()

        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        ttk.Label(
            self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W
        ).pack(fill=tk.X, padx=5, pady=5)

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
                    if file.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
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
            original_img.thumbnail((400, 400))
            original_tk = ImageTk.PhotoImage(original_img)
            self.original_img_label.configure(image=original_tk)
            self.original_img_label.image = original_tk

            # 显示原图信息
            file_size = os.path.getsize(self.current_image) / 1024
            self.original_info.config(
                text=f"原图路径: {self.current_image}\n"
                f"大小: {file_size:.1f}KB\n"
                f"尺寸: {original_img.width}x{original_img.height}"
            )

            # 自动计算压缩并显示结果
            self.auto_compress_and_show(original_img)

        except Exception as e:
            messagebox.showerror("错误", f"无法加载图片: {str(e)}")

    def auto_compress_and_show(self, original_img):
        """自动计算压缩比例并显示结果"""
        try:
            start_time = time.time()

            # 自动计算压缩质量
            compressed_img, quality, compressed_size = (
                self.calculate_optimal_compression(original_img)
            )

            # 显示压缩图
            compressed_img.thumbnail((400, 400))
            compressed_tk = ImageTk.PhotoImage(compressed_img)
            self.compressed_img_label.configure(image=compressed_tk)
            self.compressed_img_label.image = compressed_tk

            # 显示压缩信息
            self.compressed_info.config(
                text=f"压缩质量: {quality}%\n"
                f"目标大小: {self.target_size_kb}KB\n"
                f"实际大小: {compressed_size:.1f}KB\n"
                f"处理时间: {time.time()-start_time:.2f}秒"
            )

        except Exception as e:
            messagebox.showerror("错误", f"压缩图片失败: {str(e)}")

    def calculate_optimal_compression(self, img):
        target_kb = self.target_size_kb
        min_q, max_q = 20, 95
        best_bytes = None
        best_quality = None
        closest_diff = float("inf")

        for _ in range(10):  # 最多尝试 10 次
            mid_q = (min_q + max_q) // 2
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=mid_q, optimize=True)
            data = buffer.getvalue()
            size_kb = len(data) / 1024

            diff = abs(size_kb - target_kb)
            if diff < closest_diff:
                best_bytes = data
                best_quality = mid_q
                closest_diff = diff

            # 收敛条件
            if target_kb * 0.98 <= size_kb <= target_kb * 1.02:
                break

            # 二分法调节质量
            if size_kb > target_kb:
                max_q = mid_q - 1
            else:
                min_q = mid_q + 1

        final_img = Image.open(io.BytesIO(best_bytes))
        final_size_kb = len(best_bytes) / 1024
        return final_img, best_quality, final_size_kb

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

        # 创建进度标签（放在状态栏上方）
        progress_frame = ttk.Frame(self.root)
        progress_frame.pack(fill=tk.X, padx=5, pady=2)

        progress_label = ttk.Label(progress_frame, text="当前进度:")
        progress_label.pack(side=tk.LEFT)

        progress_text = tk.StringVar()
        progress_text.set("等待开始...")
        progress_display = ttk.Label(progress_frame, textvariable=progress_text)
        progress_display.pack(side=tk.LEFT, padx=5)

        # 添加取消按钮
        cancel_var = tk.BooleanVar(value=False)
        ttk.Button(
            progress_frame, text="取消", command=lambda: cancel_var.set(True)
        ).pack(side=tk.RIGHT)

        start_time = time.time()

        for img_path in self.image_files:
            if cancel_var.get():
                self.status_var.set("用户取消压缩")
                break

            processed += 1
            self.status_var.set(f"正在压缩: {processed}/{total} (跳过:{skipped})")
            progress_text.set(os.path.basename(img_path))

            # 更新当前处理的图片显示
            self.current_image = img_path
            try:
                img = Image.open(img_path)
                img.thumbnail((200, 200))  # 缩略图用于显示
                current_img = ImageTk.PhotoImage(img)
                self.original_img_label.configure(image=current_img)
                self.original_img_label.image = current_img
                self.original_info.config(
                    text=f"正在处理: {os.path.basename(img_path)}\n"
                    f"原始大小: {os.path.getsize(img_path)/1024:.1f}KB"
                )
            except Exception as e:
                print(f"无法显示图片: {str(e)}")

            self.root.update()  # 强制刷新UI

            # 获取相对路径
            rel_path = os.path.relpath(img_path, self.output_folder)
            dest_path = os.path.join(self.compressed_folder, rel_path)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            # 获取原始大小
            original_size = os.path.getsize(img_path) / 1024

            # 如果小于目标大小，直接复制
            if original_size <= self.target_size_kb * 1.1:
                shutil.copy2(img_path, dest_path)
                skipped += 1
                self.report_data.append(
                    {
                        "file": img_path,
                        "original_size": original_size,
                        "compressed_size": original_size,
                        "status": "skipped (already small enough)",
                        "destination": dest_path,
                    }
                )
                continue

            try:
                # 压缩图片
                img = Image.open(img_path)
                preview_img = self.resize_for_preview(img, max_size=(200, 200))
                # 预览图
                current_img = ImageTk.PhotoImage(preview_img)
                self.original_img_label.configure(image=current_img)
                self.original_img_label.image = current_img

                # 压缩图片
                img = Image.open(img_path)
                compressed_img, quality, compressed_size = (
                    self.calculate_optimal_compression(img)
                )

                # 显示压缩图（仅缩放显示）
                compressed_preview = self.resize_for_preview(
                    compressed_img, max_size=(200, 200)
                )
                compressed_preview_tk = ImageTk.PhotoImage(compressed_preview)
                self.compressed_img_label.configure(image=compressed_preview_tk)
                self.compressed_img_label.image = compressed_preview_tk

                # 保存压缩后的图片
                compressed_img.save(dest_path, quality=quality, optimize=True)

                # 记录到报告
                self.report_data.append(
                    {
                        "file": img_path,
                        "original_size": original_size,
                        "compressed_size": compressed_size,
                        "quality": quality,
                        "status": "success",
                        "destination": dest_path,
                    }
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
                        "destination": dest_path,
                    }
                )

        # 清理进度显示
        progress_frame.pack_forget()

        if not cancel_var.get():
            elapsed = time.time() - start_time
            messagebox.showinfo(
                "完成",
                f"图片压缩完成!\n\n"
                f"处理总数: {total}\n"
                f"成功压缩: {total - skipped}\n"
                f"跳过(已足够小): {skipped}\n"
                f"耗时: {elapsed:.1f}秒",
            )
            self.status_var.set(f"压缩完成! 结果保存在: {self.compressed_folder}")

    def generate_report(self):
        if not self.report_data:
            messagebox.showwarning("警告", "没有可用的压缩数据，请先执行压缩")
            return

        # 创建Markdown报告
        report = f"# 图片压缩报告\n\n"
        report += f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        report += "## 文件处理详情\n\n"
        report += "| 原文件路径 | 原始大小(KB) | 压缩后大小(KB) | 压缩质量 | 状态 | 保存路径 |\n"
        report += "|------------|-------------|----------------|----------|------|----------|\n"

        for item in self.report_data:
            quality = item.get("quality", "N/A")
            report += (
                f"| {item['file']} | {item['original_size']:.1f} | "
                f"{item['compressed_size']:.1f} | {quality} | "
                f"{item['status']} | {item['destination']} |\n"
            )

        # 统计信息
        success_count = len([x for x in self.report_data if x["status"] == "success"])
        skipped_count = len(
            [x for x in self.report_data if "skipped" in str(x["status"])]
        )
        failed_count = len(
            [x for x in self.report_data if "failed" in str(x["status"])]
        )

        report += "\n## 统计信息\n\n"
        report += f"- 总文件数: {len(self.report_data)}\n"
        report += f"- 成功压缩: {success_count}\n"
        report += f"- 跳过(已足够小): {skipped_count}\n"
        report += f"- 失败: {failed_count}\n"

        # 保存报告
        report_path = os.path.join(
            os.path.dirname(self.compressed_folder), "compression_report.md"
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        # 转换为HTML
        html = markdown.markdown(report)
        html_path = os.path.join(
            os.path.dirname(self.compressed_folder), "compression_report.html"
        )
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(f"<html><body>{html}</body></html>")

        messagebox.showinfo(
            "报告生成成功",
            f"Markdown和HTML报告已生成:\n\n" f"{report_path}\n" f"{html_path}",
        )
        self.status_var.set(f"报告已生成: {report_path}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageCompressorApp(root)
    root.mainloop()
