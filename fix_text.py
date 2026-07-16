import sys
import re

file_path = 'frontend/src/pages/Dashboard.tsx'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

replacements = [
    # Live Analysis & Risk Engine Title
    ('text-sm font-bold uppercase tracking-[0.2em] text-[#496b52]', 'text-lg font-bold uppercase tracking-[0.2em] text-[#496b52]'),
    ('text-4xl lg:text-5xl font-extrabold text-[#26201b]', 'text-5xl lg:text-6xl font-extrabold text-[#26201b]'),
    
    # Form labels & inputs
    ("labelCls = 'block text-xs", "labelCls = 'block text-sm"),
    ("inputCls = 'w-full bg-[#f4efe6] border border-[#d8cbb0] rounded-lg px-3 py-2 text-sm", "inputCls = 'w-full bg-[#f4efe6] border border-[#d8cbb0] rounded-lg px-3 py-2 text-base"),
    
    # Headers like 'User Activity Input'
    ('text-sm text-[#26201b] uppercase tracking-wider mb-3 font-bold', 'text-base text-[#26201b] uppercase tracking-wider mb-3 font-bold'),
    ('text-xs font-semibold text-[#26201b] uppercase tracking-wider', 'text-sm font-semibold text-[#26201b] uppercase tracking-wider'),
    
    # Narrative explanation paragraph
    ('text-sm text-[#26201b] leading-relaxed', 'text-base text-[#26201b] leading-relaxed'),
    
    # Enforcement Actions
    ('text-sm font-bold text-[#26201b] uppercase tracking-wider\">Enforcement Actions', 'text-lg font-bold text-[#26201b] uppercase tracking-wider\">Enforcement Actions'),
    ('text-sm text-[#26201b] font-bold\">{result.recommended_actions.length} recommended', 'text-base text-[#26201b] font-bold\">{result.recommended_actions.length} recommended'),
    
    # Sigma text
    ('text-[11px] text-[#544c41] font-medium', 'text-xs text-[#544c41] font-medium'),
    
    # Action cards text
    ('text-sm font-medium text-[#26201b]', 'text-base font-medium text-[#26201b]'),
    
    # Risk score labels
    ('text-xs text-[#26201b] uppercase tracking-widest\">Risk Score', 'text-sm text-[#26201b] uppercase tracking-widest font-bold\">Risk Score'),
]

new_content = content
for old, new in replacements:
    new_content = new_content.replace(old, new)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)
print('Replaced classes successfully.')
