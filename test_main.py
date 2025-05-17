import unittest
import os
from unittest.mock import patch, MagicMock, mock_open
from unittest import mock
import shutil
import hashlib
from PySide6.QtWidgets import QFileDialog 
from main import (
    select_folder, get_file_info, hash_file,
    sort_by_type, sort_by_similarity, move_files_into_one_folder,
    organize_files, move_duplicates,
    TYPE_PREFIX, NO_EXTENSION_FOLDER, SIMILAR_PREFIX, ALL_FILES_FOLDER,
    DUPLICATES_FOLDER, DUPLICATE_PREFIX, EMPTY_FOLDERS_FOLDER
)

class TestDirectoryOrganizer(unittest.TestCase):

    # === File Handling Functions ===

    @patch('main.QFileDialog')
    def test_select_folder_valid_selection(self, mock_dialog):
        mock_dialog_instance = MagicMock()
        mock_dialog.return_value = mock_dialog_instance
        mock_dialog.FileMode = QFileDialog.FileMode
        mock_dialog_instance.exec.return_value = True
        mock_dialog_instance.selectedFiles.return_value = ['/selected/folder']
        mock_dialog_instance.directory.return_value.absolutePath.return_value = '/selected'
        result = select_folder(None)
        self.assertEqual(result, '/selected/folder')
        mock_dialog_instance.setFileMode.assert_called_with(QFileDialog.FileMode.Directory)
#        mock_dialog_instance.setOption.assert_called_with(QFileDialog.Option.DontUseNativeDialog, True)

    @patch('main.QFileDialog')
    def test_select_folder_no_selection(self, mock_dialog):
        # Setup mock
        mock_dialog_instance = MagicMock()
        mock_dialog.return_value = mock_dialog_instance
        mock_dialog_instance.exec.return_value = False

        # Call function
        result = select_folder(None)

        # Assert
        self.assertIsNone(result)

    @patch('os.scandir')
    def test_get_file_info_single_file(self, mock_scandir):
        # Setup mock
        mock_entry = MagicMock()
        mock_entry.is_file.return_value = True
        mock_entry.is_dir.return_value = False
        mock_entry.path = '/test/file.txt'
        mock_entry.name = 'file.txt'
        mock_scandir.return_value.__enter__.return_value = [mock_entry]

        # Call function
        files, duplicates = get_file_info('/test')

        # Assert
        expected_files = [{
            'path': '/test/file.txt',
            'name': 'file.txt',
            'ext': '.txt',
            'words': ['file']
        }]
        self.assertEqual(files, expected_files)
        self.assertEqual(duplicates, [])

    @patch('os.scandir')
    def test_get_file_info_duplicate_files(self, mock_scandir):
        # Setup mock
        mock_entry1 = MagicMock()
        mock_entry1.is_file.return_value = True
        mock_entry1.is_dir.return_value = False
        mock_entry1.path = '/test/file.txt'
        mock_entry1.name = 'file.txt'

        mock_entry2 = MagicMock()
        mock_entry2.is_file.return_value = True
        mock_entry2.is_dir.return_value = False
        mock_entry2.path = '/test/sub/file.txt'
        mock_entry2.name = 'file.txt'

        mock_scandir.return_value.__enter__.return_value = [mock_entry1, mock_entry2]

        # Call function
        files, duplicates = get_file_info('/test', recursive=True)

        # Assert
        expected_files = [{
            'path': '/test/file.txt',
            'name': 'file.txt',
            'ext': '.txt',
            'words': ['file']
        }]
        self.assertEqual(files, expected_files)
        self.assertEqual(duplicates, ['/test/sub/file.txt'])

    @patch('builtins.open', new_callable=mock_open, read_data=b"test content")
    def test_hash_file(self, mock_file):
        # Call function
        result = hash_file('/test/file.txt')

        # Assert
        expected_hash = hashlib.md5(b"test content").hexdigest()
        self.assertEqual(result, expected_hash)
        mock_file.assert_called_with('/test/file.txt', 'rb')

    # === Sorting Functions ===

    def test_sort_by_type_no_recursive(self):
        files = [
            {'path': '/test/file1.txt', 'name': 'file1.txt', 'ext': '.txt', 'words': ['file1']},
            {'path': '/test/file2.pdf', 'name': 'file2.pdf', 'ext': '.pdf', 'words': ['file2']},
            {'path': '/test/file3.txt', 'name': 'file3.txt', 'ext': '.txt', 'words': ['file3']}
        ]
        suggestions = sort_by_type(files)

        expected = {
            'Type txt': ['/test/file1.txt', '/test/file3.txt'],
            'Type pdf': ['/test/file2.pdf']
        }
        self.assertEqual(suggestions, expected)

    def test_sort_by_type_recursive(self):
        files = [
            {'path': '/test/file1.txt', 'name': 'file1.txt', 'ext': '.txt', 'words': ['file1']},
            {'path': '/test/file2.txt', 'name': 'file2.txt', 'ext': '.txt', 'words': ['file2']}
        ]
        suggestions = sort_by_type(files, recursive=True, base_path='/test')

        expected = {
            'Type txt': ['/test/file1.txt', '/test/file2.txt']
        }
        self.assertEqual(suggestions, expected)

    def test_sort_by_type_no_extension(self):
        files = [
            {'path': '/test/file1', 'name': 'file1', 'ext': '.no_extension', 'words': ['file1']}
        ]
        suggestions = sort_by_type(files)

        expected = {
            'No Extension': ['/test/file1']
        }
        self.assertEqual(suggestions, expected)

    @patch('main.hash_file')
    def test_sort_by_similarity_contents(self, mock_hash):
        files = [
            {'path': '/test/file1.txt', 'name': 'file1.txt', 'ext': '.txt', 'words': ['file1']},
            {'path': '/test/file2.txt', 'name': 'file2.txt', 'ext': '.txt', 'words': ['file2']}
        ]
        mock_hash.side_effect = ['hash1', 'hash1']
        suggestions = sort_by_similarity(files, check_contents=True)

        expected = {
            'Similar1': ['/test/file1.txt', '/test/file2.txt']
        }
        self.assertEqual(suggestions, expected)

    def test_sort_by_similarity_names(self):
        files = [
            {'path': '/test/doc1.txt', 'name': 'doc1.txt', 'ext': '.txt', 'words': ['doc1']},
            {'path': '/test/doc2.txt', 'name': 'doc2.txt', 'ext': '.txt', 'words': ['doc2']}
        ]
        suggestions = sort_by_similarity(files, check_contents=False)

        expected = {
            'Similar1': ['/test/doc1.txt', '/test/doc2.txt']
        }
        self.assertEqual(suggestions, expected)

    def test_move_files_into_one_folder(self):
        files = [
            {'path': '/test/file1.txt', 'name': 'file1.txt', 'ext': '.txt', 'words': ['file1']},
            {'path': '/test/file2.pdf', 'name': 'file2.pdf', 'ext': '.pdf', 'words': ['file2']}
        ]
        suggestions = move_files_into_one_folder(files)

        expected = {
            'One Folder': ['/test/file1.txt', '/test/file2.pdf']
        }
        self.assertEqual(suggestions, expected)

    def test_move_files_into_one_folder_empty(self):
        suggestions = move_files_into_one_folder([])
        self.assertEqual(suggestions, {})

    # === File Organization Functions ===

    @patch('os.makedirs')
    @patch('shutil.move')
    def test_organize_files_basic(self, mock_move, mock_makedirs):
        suggestions = {
            'Type txt': ['/test/file1.txt', '/test/file2.txt']
        }
        organize_files(suggestions, base_path='/test')

        mock_makedirs.assert_called_with('/test/Type txt', exist_ok=True)
        mock_move.assert_any_call('/test/file1.txt', '/test/Type txt/file1.txt')
        mock_move.assert_any_call('/test/file2.txt', '/test/Type txt/file2.txt')

    @patch('os.makedirs')
    @patch('shutil.move')
    @patch('os.walk')
    @patch('os.listdir')
    @patch('shutil.rmtree')
    def test_organize_files_delete_empty(self, mock_rmtree, mock_listdir, mock_walk, mock_move, mock_makedirs):
        suggestions = {'Type txt': ['/test/file1.txt']}
        walk_data = [('/test', ['empty'], ['file1.txt']), ('/test/empty', [], [])]
        mock_walk.return_value = walk_data
        mock_listdir.side_effect = [['file1.txt'], [], []]
        organize_files(suggestions, recursive=True, cleanup=True, delete_empty=True, base_path='/test')
        mock_makedirs.assert_called_with('/test/Type txt', exist_ok=True)
        mock_move.assert_called_with('/test/file1.txt', '/test/Type txt/file1.txt')
        mock_rmtree.assert_called_with('/test/empty')        

    @patch('os.makedirs')
    @patch('shutil.move')
    @patch('os.walk')
    @patch('os.listdir')
    def test_organize_files_move_empty(self, mock_listdir, mock_walk, mock_move, mock_makedirs):
        suggestions = {'Type txt': ['/test/file1.txt']}
        walk_data = [('/test', ['empty'], ['file1.txt']), ('/test/empty', [], [])]
        mock_walk.return_value = walk_data
        mock_listdir.side_effect = [['file1.txt'], [], []]
        organize_files(suggestions, recursive=True, cleanup=True, delete_empty=False, base_path='/test')
        mock_makedirs.assert_any_call('/test/Empty Folders', exist_ok=True)
        mock_makedirs.assert_any_call('/test/Type txt', exist_ok=True)
        mock_move.assert_any_call('/test/file1.txt', '/test/Type txt/file1.txt')
        mock_move.assert_any_call('/test/empty', '/test/Empty Folders/empty')

    @patch('os.makedirs')
    @patch('shutil.move')
    @patch('os.path.exists')
    def test_move_duplicates_names(self, mock_exists, mock_move, mock_makedirs):
        existing_paths = set()
        def exists_side_effect(path):
            return path in existing_paths
        mock_exists.side_effect = exists_side_effect
        existing_paths.add('/test/Duplicates/Dupe0_file.txt')
        duplicates = ['/source/file.txt']
        move_duplicates(duplicates, '/test/', check_contents=False)
        print(mock_move.call_args_list)
        mock_makedirs.assert_called_with('/test/Duplicates', exist_ok=True)
        mock_move.assert_any_call('/source/file.txt', '/test/Duplicates/Dupe0_file1.txt')

    # === Edge Cases ===

    @patch('os.scandir')
    def test_get_file_info_empty_folder(self, mock_scandir):
        mock_scandir.return_value.__enter__.return_value = []
        files, duplicates = get_file_info('/test')
        self.assertEqual(files, [])
        self.assertEqual(duplicates, [])

    def test_sort_by_type_empty(self):
        suggestions = sort_by_type([])
        self.assertEqual(suggestions, {})

    def test_sort_by_similarity_empty(self):
        suggestions = sort_by_similarity([])
        self.assertEqual(suggestions, {})

    @patch('os.makedirs')
    def test_organize_files_empty_suggestions(self, mock_makedirs):
        organize_files({}, base_path='/test')
        mock_makedirs.assert_not_called()

    @patch('os.makedirs')
    def test_move_duplicates_empty(self, mock_makedirs):
        move_duplicates([], '/test')
        mock_makedirs.assert_not_called()

if __name__ == '__main__':
    unittest.main()
