"""
文档文本提取模块 - 支持TXT和PDF格式
"""
import os
import re
import pdfplumber


# 零宽字符、BOM等不可见字符
_INVISIBLE_CHARS = re.compile('[\\u200b-\\u200f\\ufeff]')
# 中日韩文字及常见中文标点
_CJK_CHAR = r'[一-鿿㐀-䶿豈-﫿　-〿＀-￯]'


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
    return _normalize_pdf_text('\n'.join(text_parts))


def _normalize_pdf_text(text: str) -> str:
    """
    规范化PDF提取文本。

    PDF按坐标还原文本时，经常在中文之间插入空格，或在段落中间插入换行。
    这些字符会导致实体被存成带空格的形式，从而无法被问答关键词命中。
    """
    text = _INVISIBLE_CHARS.sub('', text)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # 统一空白字符，同时保留换行作为后续句子边界处理依据
    text = re.sub(r'[^\S\n]+', ' ', text)

    # 去除中文与相邻字符之间由PDF布局产生的空白（中文与数字/英文之间也不应有空格）。
    # 两个英文单词之间的空格保留，避免破坏英文短语。
    text = re.sub(rf'{_CJK_CHAR}[^\S\n]+', lambda m: m.group()[0], text)
    text = re.sub(rf'[^\S\n]+(?={_CJK_CHAR})', '', text)

    # 仅合并未以句末标点结束的PDF折行；保留段落和句子换行，避免错误拼接两句话。
    text = re.sub(rf'({_CJK_CHAR})(?<![。！？；：，、])\n(?={_CJK_CHAR})', r'\1', text)
    text = re.sub(rf'({_CJK_CHAR})(?<![。！？；：，、])\n(?=[A-Za-z0-9])', r'\1', text)

    # PDF段落折行后若下一行以英文/数字开头，补空格以避免英文单词粘连
    text = re.sub(r'([A-Za-z0-9])\n([A-Za-z0-9])', r'\1 \2', text)
    # 去除行首、行尾残留空白
    text = '\n'.join(line.strip() for line in text.split('\n'))
    return text.strip()
