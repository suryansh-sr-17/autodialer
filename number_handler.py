import re
import logging
from typing import List, Tuple, Dict, Set
from config import Config

logger = logging.getLogger(__name__)

class NumberHandler:
    """
    Handles phone number validation, parsing, and processing for the autodialer system.
    Supports Indian phone number formats and test mode validation.
    """
    
    def __init__(self):
        self.test_mode = Config.TEST_MODE
        
        # Indian phone number patterns
        self.mobile_pattern = r'^(\+91|91)?[6-9]\d{9}$'
        self.toll_free_pattern = r'^(\+91|91)?1800\d{7}$'
        self.landline_pattern = r'^(\+91|91)?\d{2,4}\d{6,8}$'
        
        # Test mode pattern (only 1800 numbers)
        self.test_pattern = r'^(\+91|91)?1800\d{7}$'
        
        # Compiled regex patterns for better performance
        self.compiled_patterns = {
            'mobile': re.compile(self.mobile_pattern),
            'toll_free': re.compile(self.toll_free_pattern),
            'landline': re.compile(self.landline_pattern),
            'test': re.compile(self.test_pattern)
        }
    
    def clean_number(self, number: str) -> str:
        """
        Clean phone number by removing spaces, dashes, brackets, and other non-digit characters.
        Preserves the + sign for country code.
        """
        if not number or not isinstance(number, str):
            return ""
        
        # Remove all characters except digits and +
        cleaned = re.sub(r'[^\d+]', '', number.strip())
        return cleaned
    
    def normalize_number(self, number: str) -> str:
        """
        Normalize phone number to standard +91 format.
        """
        cleaned = self.clean_number(number)
        
        if not cleaned:
            return ""
        
        # If already has +91, return as is
        if cleaned.startswith('+91'):
            return cleaned
        
        # If starts with 91, add +
        if cleaned.startswith('91'):
            return '+' + cleaned
        
        # If starts with 0, remove it and add +91
        if cleaned.startswith('0'):
            cleaned = cleaned[1:]
        
        # Add +91 prefix
        return '+91' + cleaned
    
    def validate_single_number(self, number: str) -> Tuple[bool, str, str]:
        """
        Validate a single phone number.
        
        Returns:
            Tuple[bool, str, str]: (is_valid, normalized_number_or_error, number_type)
        """
        if not number or not isinstance(number, str):
            return False, "Phone number must be a non-empty string", ""
        
        cleaned = self.clean_number(number)
        
        if not cleaned:
            return False, "Phone number contains no valid digits", ""
        
        # Test mode validation
        if self.test_mode:
            if self.compiled_patterns['test'].match(cleaned):
                normalized = self.normalize_number(cleaned)
                return True, normalized, "toll_free"
            else:
                return False, "In test mode, only 1800 XXXX XXXX numbers are allowed", ""
        
        # Production mode validation
        number_type = ""
        
        # Check mobile numbers
        if self.compiled_patterns['mobile'].match(cleaned):
            number_type = "mobile"
        # Check toll-free numbers
        elif self.compiled_patterns['toll_free'].match(cleaned):
            number_type = "toll_free"
        # Check landline numbers
        elif self.compiled_patterns['landline'].match(cleaned):
            number_type = "landline"
        else:
            return False, "Invalid Indian phone number format", ""
        
        normalized = self.normalize_number(cleaned)
        return True, normalized, number_type
    
    def validate_multiple_numbers(self, numbers: List[str]) -> Dict[str, List]:
        """
        Validate multiple phone numbers and categorize results.
        
        Returns:
            Dict with 'valid', 'invalid', and 'duplicates' lists
        """
        results = {
            'valid': [],
            'invalid': [],
            'duplicates': []
        }
        
        seen_numbers = set()
        
        for number in numbers:
            is_valid, result, number_type = self.validate_single_number(number)
            
            if is_valid:
                if result in seen_numbers:
                    results['duplicates'].append({
                        'original': number,
                        'normalized': result,
                        'type': number_type
                    })
                else:
                    seen_numbers.add(result)
                    results['valid'].append({
                        'original': number,
                        'normalized': result,
                        'type': number_type
                    })
            else:
                results['invalid'].append({
                    'original': number,
                    'error': result
                })
        
        return results
    
    def parse_text_input(self, text: str) -> List[str]:
        """
        Parse phone numbers from text input (copy-paste).
        Supports multiple formats: comma-separated, line-separated, space-separated.
        """
        if not text or not isinstance(text, str):
            return []
        
        # Split by common delimiters
        delimiters = ['\n', '\r\n', ',', ';', '\t']
        numbers = [text]
        
        for delimiter in delimiters:
            temp_numbers = []
            for num in numbers:
                temp_numbers.extend(num.split(delimiter))
            numbers = temp_numbers
        
        # Clean and filter empty strings
        cleaned_numbers = []
        for number in numbers:
            cleaned = number.strip()
            if cleaned:
                cleaned_numbers.append(cleaned)
        
        return cleaned_numbers
    
    def remove_duplicates(self, numbers: List[str]) -> Tuple[List[str], List[str]]:
        """
        Remove duplicate phone numbers from a list.
        
        Returns:
            Tuple[List[str], List[str]]: (unique_numbers, duplicates)
        """
        seen = set()
        unique = []
        duplicates = []
        
        for number in numbers:
            is_valid, normalized, _ = self.validate_single_number(number)
            
            if is_valid:
                if normalized in seen:
                    duplicates.append(number)
                else:
                    seen.add(normalized)
                    unique.append(number)
            else:
                # Keep invalid numbers for separate processing
                unique.append(number)
        
        return unique, duplicates
    
    def extract_numbers_from_text(self, text: str) -> List[str]:
        """
        Extract phone numbers from free-form text using regex patterns.
        Useful for parsing mixed content.
        """
        if not text:
            return []
        
        # Patterns to match phone numbers in text
        patterns = [
            r'\+91[6-9]\d{9}',  # +91 mobile
            r'\+911800\d{7}',   # +91 toll-free
            r'91[6-9]\d{9}',    # 91 mobile
            r'911800\d{7}',     # 91 toll-free
            r'[6-9]\d{9}',      # 10-digit mobile
            r'1800\d{7}',       # 11-digit toll-free
            r'0[6-9]\d{9}',     # 11-digit with leading 0
        ]
        
        found_numbers = []
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            found_numbers.extend(matches)
        
        # Remove duplicates while preserving order
        unique_numbers = []
        seen = set()
        
        for number in found_numbers:
            if number not in seen:
                seen.add(number)
                unique_numbers.append(number)
        
        return unique_numbers
    
    def get_number_statistics(self, numbers: List[str]) -> Dict[str, int]:
        """
        Get statistics about a list of phone numbers.
        """
        validation_results = self.validate_multiple_numbers(numbers)
        
        stats = {
            'total_input': len(numbers),
            'valid_count': len(validation_results['valid']),
            'invalid_count': len(validation_results['invalid']),
            'duplicate_count': len(validation_results['duplicates']),
            'mobile_count': 0,
            'toll_free_count': 0,
            'landline_count': 0
        }
        
        # Count by type
        for number_info in validation_results['valid']:
            number_type = number_info['type']
            if number_type == 'mobile':
                stats['mobile_count'] += 1
            elif number_type == 'toll_free':
                stats['toll_free_count'] += 1
            elif number_type == 'landline':
                stats['landline_count'] += 1
        
        return stats
    
    def format_number_for_display(self, number: str) -> str:
        """
        Format phone number for user-friendly display.
        """
        is_valid, normalized, number_type = self.validate_single_number(number)
        
        if not is_valid:
            return number  # Return original if invalid
        
        # Format based on type
        if number_type == 'mobile':
            # Format as +91 XXXXX XXXXX
            if len(normalized) == 13:  # +91XXXXXXXXXX
                return f"{normalized[:3]} {normalized[3:8]} {normalized[8:]}"
        elif number_type == 'toll_free':
            # Format as +91 1800 XXX XXXX
            if len(normalized) == 14:  # +911800XXXXXXX
                return f"{normalized[:3]} {normalized[3:7]} {normalized[7:10]} {normalized[10:]}"
        
        return normalized
    
    def is_test_number(self, number: str) -> bool:
        """
        Check if a number is a valid test number (1800 format).
        """
        cleaned = self.clean_number(number)
        return bool(self.compiled_patterns['test'].match(cleaned))
    
    def get_number_type(self, number: str) -> str:
        """
        Get the type of phone number (mobile, toll_free, landline).
        """
        is_valid, _, number_type = self.validate_single_number(number)
        return number_type if is_valid else "invalid"