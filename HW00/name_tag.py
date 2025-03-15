from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

def register_chinese_font():
    """注册一个支持中文的字体，优先尝试macOS常见的中文字体"""
    # 定义常见的macOS中文字体及其可能的路径
    mac_fonts = [
        {"name": "PingFang SC", "path": "/System/Library/Fonts/PingFang.ttc"},
        {"name": "STHeiti", "path": "/System/Library/Fonts/STHeiti Light.ttc"}, 
        {"name": "Hiragino Sans GB", "path": "/System/Library/Fonts/Hiragino Sans GB.ttc"},
        {"name": "Apple LiGothic", "path": "/System/Library/Fonts/Apple LiGothic Medium.ttf"}
    ]
    
    # 尝试每一个字体直到成功
    for font in mac_fonts:
        font_name = font["name"]
        font_path = font["path"]
        
        # 检查字体是否已经注册
        if font_name in pdfmetrics.getRegisteredFontNames():
            return font_name
            
        # 检查字体文件是否存在
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                print(f"成功注册字体: {font_name}")
                return font_name
            except Exception as e:
                print(f"尝试注册字体 {font_name} 失败: {e}")
                continue
    
    # 如果所有字体都失败，尝试自动检测系统字体
    try:
        import matplotlib.font_manager as fm
        system_fonts = fm.findSystemFonts(fontext="ttf")
        for font_path in system_fonts:
            if "chinese" in font_path.lower() or "cjk" in font_path.lower():
                try:
                    font_name = os.path.basename(font_path).split(".")[0]
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                    print(f"自动检测并注册字体: {font_name}")
                    return font_name
                except Exception:
                    continue
    except ImportError:
        print("无法自动检测系统字体，请确保安装了matplotlib包")
    
    print("警告: 未能找到支持中文的字体，将使用默认字体")
    return "Helvetica"  # 回退到默认字体（不支持中文）

def create_nameplate_pdf(name, output_filename="nameplate.pdf", size=100):
    # A4页面尺寸 (宽度: 210mm, 高度: 297mm)
    width, height = A4
    
    # 创建PDF
    c = canvas.Canvas(output_filename, pagesize=A4)
    
    # 注册并设置中文字体
    font_name = register_chinese_font()
    c.setFont(font_name, size)
    
    # 计算每个面的高度 (三分之一页面高度)
    section_height = height / 3
    
    # 添加折叠虚线
    c.setDash(5, 3)  # 设置虚线样式
    c.setLineWidth(0.5)
    c.line(0, section_height, width, section_height)  # 第一条虚线
    c.line(0, 2 * section_height, width, 2 * section_height)  # 第二条虚线
    c.setDash(1, 0)  # 恢复实线
    
    # 计算文字宽度和高度，用于垂直居中
    # ReportLab中文字高度大约为字体大小的70%
    text_height = size * 0.7
    # 获取文字宽度
    from reportlab.pdfbase.pdfmetrics import stringWidth
    text_width = stringWidth(name, font_name, size)
    
    # 第一个面 (反向姓名，位于顶部)
    c.saveState()
    # 移动到第一个面的中心，考虑字体高度进行微调
    c.translate(width / 2, 2.5 * section_height + text_height/2)
    c.rotate(180)  # 旋转180度，使文字反向
    c.drawCentredString(0, 0, name)
    c.restoreState()
    
    # 第二个面 (正向姓名，位于中间)
    c.saveState()
    # 移动到第二个面的中心，考虑字体高度进行微调
    c.translate(width / 2, 1.5 * section_height - text_height/2)
    c.drawCentredString(0, 0, name)
    c.restoreState()
    
    # 第三个面 (底部空白，无文字)
    # 不需要额外操作，保持空白
    
    # 保存PDF
    c.showPage()
    c.save()
    print(f"PDF 文件已生成: {output_filename}")
    print(f"文字信息: 宽度={text_width:.1f}pt, 高度≈{text_height:.1f}pt")

def main():
    # 获取用户输入的姓名
    name = input("请输入姓名: ")
    
    # 获取用户输入的字体大小
    try:
        size = int(input("请输入字体大小(默认100): ") or "100")
    except ValueError:
        size = 100
        print("输入无效，使用默认字体大小: 100")
    
    output_filename = f"{name}_nameplate.pdf"
    
    # 创建PDF
    create_nameplate_pdf(name, output_filename, size)
    
    # 提示用户如何折叠
    print("\n折叠说明:")
    print("1. 将生成的PDF打印到A4纸上。")
    print("2. 沿着两条虚线折叠纸张，使其形成一个三棱柱。")
    print("3. 折叠后，底部为空白面，另两个面显示姓名。")

if __name__ == "__main__":
    main()
