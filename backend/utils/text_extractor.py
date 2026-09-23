"""
文档文本提取模块 - 支持TXT和PDF格式
"""
import os
import re

import pdfplumber


# PDF 提取中文文本时，常见的 CJK 字符范围
_CJK_CHAR = r'\u3400-\u4dbf\u4e00-\u9fff\u8c48-\ufaff'
_CJK_PUNCT = '，。！？；：、（）《》【】「」“”‘’…—·'
_HORIZONTAL_SPACE = r'[ \t　]*'
_INVISIBLE_CHARS = r'[\ufeff\u200b-\u200f\u2060]'


def extract_text(file_path: str) -> str:
    """从文件中提取文本内容"""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.txt':
        return _extract_from_txt(file_path)
    elif ext == '.pdf':
        return _extract_from_pdf(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")


def _extract_from_txt(file_path: str) -> str:
    """从TXT文件提取文本"""
    encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(f"无法解码文件: {file_path}")


def _extract_from_pdf(file_path: str) -> str:
    """从PDF文件提取文本"""
    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    # 统一在整篇文本上规范化，避免跨页句子或实体被页边界截断
    return _normalize_pdf_text('\n'.join(text_parts))


def _normalize_pdf_text(text: str) -> str:
    """
    规范化 pdfplumber 提取出的版式文本。

    PDF 中的换行和空格只用于页面排版，并不一定代表语义分隔。PDF 中的
    中文实体被换行或空格拆开后，会与问答输入中的完整实体不一致，导致
    三元组已存在但检索不到。这里在进入 NLP 前统一清理这些排版字符。
    """
    # 统一换行形式，避免 Windows/PDF 提取结果中的回车影响后续分句
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # 移除 BOM、零宽字符等 PDF 提取时可能残留的不可见字符
    text = re.sub(_INVISIBLE_CHARS, '', text)

    # 保留空行形成的段落边界，只连接由 PDF 自动换行拆开的相邻中文行
    text = re.sub(
        rf'(?<=[{_CJK_CHAR}\w])[ \t　]*\n[ \t　]*(?=[{_CJK_CHAR}])',
        '',
        text,
    )
    text = re.sub(
        rf'(?<=[{_CJK_CHAR}])[ \t　]*\n[ \t　]*(?=\w)',
        '',
        text,
    )
    # 清理 CJK 字符之间以及 CJK 与相邻单词/中文标点之间的排版空格
    text = re.sub(
        rf'(?<=[{_CJK_CHAR}]){_HORIZONTAL_SPACE}(?=[\w{_CJK_CHAR}{re.escape(_CJK_PUNCT)}])',
        '',
        text,
    )
    text = re.sub(
        rf'(?<=[\w{re.escape(_CJK_PUNCT)}]){_HORIZONTAL_SPACE}(?=[{_CJK_CHAR}])',
        '',
        text,
    )
    text = re.sub(r'[ \t　]{2,}', ' ', text)

    lines = [line.strip() for line in text.split('\n')]
    return '\n'.join(line for line in lines if line)
