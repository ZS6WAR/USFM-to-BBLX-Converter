import sqlite3
import os
from pathlib import Path
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

class USFMToBBLXConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("USFM to e-Sword BBLX Converter")
        self.root.geometry("600x350")
        
        # Variables to store user inputs
        self.input_dir = tk.StringVar()
        self.output_file = tk.StringVar()
        self.translation_name = tk.StringVar(value="My Bible Translation")
        self.abbreviation = tk.StringVar(value="MBT")
        
        # Create GUI elements
        self.create_widgets()
    
    def create_widgets(self):
        # Version Label
        tk.Label(self.root, text="Version: 1.1 (Fixed run_conversion and grid)", fg="blue").grid(row=0, column=0, columnspan=3, padx=5, pady=5)
        
        # Input Directory
        tk.Label(self.root, text="Input Directory (USFM Files):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(self.root, textvariable=self.input_dir, width=50).grid(row=1, column=1, padx=5, pady=5)
        tk.Button(self.root, text="Browse", command=self.browse_input).grid(row=1, column=2, padx=5, pady=5)
        
        # Output File
        tk.Label(self.root, text="Output BBLX File:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(self.root, textvariable=self.output_file, width=50).grid(row=2, column=1, padx=5, pady=5)
        tk.Button(self.root, text="Browse", command=self.browse_output).grid(row=2, column=2, padx=5, pady=5)
        
        # Translation Name
        tk.Label(self.root, text="Translation Name:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(self.root, textvariable=self.translation_name, width=50).grid(row=3, column=1, columnspan=2, padx=5, pady=5)
        
        # Abbreviation
        tk.Label(self.root, text="Abbreviation:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(self.root, textvariable=self.abbreviation, width=50).grid(row=4, column=1, columnspan=2, padx=5, pady=5)
        
        # Run Button
        tk.Button(self.root, text="Run Conversion", command=self.run_conversion, bg="green", fg="white").grid(row=5, column=1, pady=20)
        
        # Status Label
        self.status = tk.Label(self.root, text="Select directories and click Run to convert.", wraplength=500)
        self.status.grid(row=6, column=0, columnspan=3, padx=5, pady=5)
    
    def browse_input(self):
        directory = filedialog.askdirectory(title="Select USFM Files Directory")
        if directory:
            self.input_dir.set(directory)
    
    def browse_output(self):
        file_path = filedialog.asksaveasfilename(
            title="Select Output BBLX File",
            defaultextension=".bblx",
            filetypes=[("BBLX Files", "*.bblx")]
        )
        if file_path:
            self.output_file.set(file_path)
    
    def create_bblx_database(self, output_file):
        """Create an e-Sword bblx SQLite database with the required schema."""
        conn = sqlite3.connect(output_file)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Bible (
                Book INTEGER,
                Chapter INTEGER,
                Verse INTEGER,
                Scripture TEXT,
                PRIMARY KEY (Book, Chapter, Verse)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Details (
                Description TEXT,
                Abbreviation TEXT,
                Comments TEXT,
                Version TEXT,
                PublishDate TEXT,
                Publisher TEXT,
                Creator TEXT,
                Language TEXT
            )
        """)
        cursor.execute("""
            INSERT INTO Details (
                Description, Abbreviation, Comments, Version, PublishDate, Publisher, Creator, Language
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.translation_name.get(),
            self.abbreviation.get(),
            "Generated from USFM files",
            "1.0",
            "2025-09-03",
            "xAI",
            "Grok",
            "af"
        ))
        conn.commit()
        return conn, cursor
    
    def get_book_number(self, book_id):
        book_map = {
            'GEN': 1, 'EXO': 2, 'LEV': 3, 'NUM': 4, 'DEU': 5,
            'JOS': 6, 'JDG': 7, 'RUT': 8, '1SA': 9, '2SA': 10,
            '1KI': 11, '2KI': 12, '1CH': 13, '2CH': 14, 'EZR': 15,
            'NEH': 16, 'EST': 17, 'JOB': 18, 'PSA': 19, 'PRO': 20,
            'ECC': 21, 'SNG': 22, 'ISA': 23, 'JER': 24, 'LAM': 25,
            'EZK': 26, 'DAN': 27, 'HOS': 28, 'JOL': 29, 'AMO': 30,
            'OBA': 31, 'JON': 32, 'MIC': 33, 'NAM': 34, 'HAB': 35,
            'ZEP': 36, 'HAG': 37, 'ZEC': 38, 'MAL': 39,
            'MAT': 40, 'MRK': 41, 'LUK': 42, 'JHN': 43, 'ACT': 44,
            'ROM': 45, '1CO': 46, '2CO': 47, 'GAL': 48, 'EPH': 49,
            'PHP': 50, 'COL': 51, '1TH': 52, '2TH': 53, '1TI': 54,
            '2TI': 55, 'TIT': 56, 'PHM': 57, 'HEB': 58, 'JAS': 59,
            '1PE': 60, '2PE': 61, '1JN': 62, '2JN': 63, '3JN': 64,
            'JUD': 65, 'REV': 66
        }
        return book_map.get(book_id.upper(), 0)
    
    def parse_usfm_file(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read().splitlines()
        
        book_id = None
        current_chapter = 0
        current_verse = 0
        verses = []
        current_text = []
        errors = []
        
        # Define metadata markers to ignore
        metadata_markers = {'\\id', '\\ide', '\\usfm', '\\h', '\\toc1', '\\toc2', '\\toc3', '\\mt1', '\\mt2'}
        
        for line_num, line in enumerate(content, 1):
            line = line.strip()
            if not line:
                continue
            
            # Skip metadata markers
            if any(line.startswith(marker) for marker in metadata_markers):
                if line.startswith('\\id '):
                    book_id = line.split()[1]
                continue
            
            if line.startswith('\\c '):
                if current_text and current_verse > 0:
                    verses.append((book_id, current_chapter, current_verse, ' '.join(current_text)))
                    current_text = []
                chapter_str = line.split()[1]
                if re.match(r'^\d+$', chapter_str):
                    current_chapter = int(chapter_str)
                    current_verse = 0
                else:
                    errors.append(f"Invalid chapter number '{chapter_str}' at line {line_num} in {file_path}")
                    continue
            elif line.startswith('\\v '):
                if current_text and current_verse > 0:
                    verses.append((book_id, current_chapter, current_verse, ' '.join(current_text)))
                    current_text = []
                parts = line.split(' ', 2)
                verse_str = parts[1] if len(parts) > 1 else ''
                if re.match(r'^\d+$', verse_str):
                    current_verse = int(verse_str)
                    current_text.append(parts[2] if len(parts) > 2 else '')
                else:
                    errors.append(f"Invalid verse number '{verse_str}' at line {line_num} in {file_path}")
                    continue
            elif line.startswith(('\\p', '\\s1')):
                if current_text:
                    current_text.append(' ')
            else:
                current_text.append(line)
        
        if current_text and current_verse > 0:
            verses.append((book_id, current_chapter, current_verse, ' '.join(current_text)))
        
        return verses, errors
    
    def convert_usfm_to_bblx(self, input_dir, output_file):
        try:
            if not input_dir or not output_file:
                messagebox.showerror("Error", "Please select both input and output directories.")
                return
            
            if not Path(input_dir).is_dir():
                messagebox.showerror("Error", "Input directory does not exist.")
                return
            
            conn, cursor = self.create_bblx_database(output_file)
            input_path = Path(input_dir)
            usfm_files = list(input_path.glob('*.usfm'))
            if not usfm_files:
                messagebox.showwarning("Warning", "No USFM files found in the input directory.")
                conn.close()
                return
            
            all_errors = []
            for usfm_file in usfm_files:
                self.status.config(text=f"Processing {usfm_file.name}...")
                self.root.update()
                verses, errors = self.parse_usfm_file(usfm_file)
                all_errors.extend(errors)
                book_id = verses[0][0] if verses else None
                book_number = self.get_book_number(book_id)
                
                if book_number == 0:
                    all_errors.append(f"Unknown book ID {book_id} in {usfm_file.name}")
                    continue
                
                for _, chapter, verse, text in verses:
                    cursor.execute("""
                        INSERT OR REPLACE INTO Bible (Book, Chapter, Verse, Scripture)
                        VALUES (?, ?, ?, ?)
                    """, (book_number, chapter, verse, text))
            
            conn.commit()
            conn.close()
            
            if all_errors:
                error_msg = "\n".join(all_errors)
                self.status.config(text="Conversion completed with errors. Check details.")
                messagebox.showwarning("Conversion Issues", f"Completed with errors:\n{error_msg}")
            else:
                self.status.config(text=f"Conversion complete! Output saved to {output_file}")
                messagebox.showinfo("Success", f"e-Sword bblx file created: {output_file}")
        
        except Exception as e:
            self.status.config(text=f"Error: {str(e)}")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
    
    def run_conversion(self):
        self.status.config(text="Converting...")
        self.root.update()
        self.convert_usfm_to_bblx(self.input_dir.get(), self.output_file.get())

def main():
    root = tk.Tk()
    app = USFMToBBLXConverter(root)
    root.mainloop()

if __name__ == "__main__":
    main()
