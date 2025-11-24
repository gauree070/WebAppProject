from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Question
import csv
import os

class Command(BaseCommand):
    help = 'Load questions from CSV into Question model'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing questions before loading',
        )
        parser.add_argument(
            '--csv-path',
            type=str,
            default='questions.csv',
            help='Path to CSV file (default: questions.csv)',
        )

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        full_path = os.path.join(settings.BASE_DIR, csv_path)
        if not os.path.exists(full_path):
            self.stdout.write(self.style.ERROR(f"CSV not found at {full_path}"))
            return

        if options['clear']:
            Question.objects.all().delete()
            self.stdout.write(self.style.WARNING('Cleared existing questions'))

        loaded_count = 0
        topic_counts = {}
        unknown_levels = set()

        with open(full_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            expected_headers = ['subject', 'topic', 'level', 'question', 'hint']
            if not all(h in reader.fieldnames for h in expected_headers):
                self.stdout.write(self.style.ERROR(f"CSV missing headers: {set(expected_headers) - set(reader.fieldnames)}"))
                return

            for row_num, row in enumerate(reader, start=2):
                try:
                    # Fixed normalization
                    level_raw = row['level'].strip().lower()
                    level_map = {'low': 'Low', 'moderate': 'Moderate', 'high': 'High'}
                    level = level_map.get(level_raw, 'Low')
                    if level == 'Low' and level_raw not in level_map:
                        unknown_levels.add(level_raw)

                    q, created = Question.objects.get_or_create(
                        topic=row['topic'].strip(),
                        question_text=row['question'].strip(),
                        defaults={
                            'subject': row.get('subject', '').strip(),
                            'level': level,
                            'hint': row['hint'].strip(),
                        }
                    )

                    if created:
                        loaded_count += 1
                        topic = q.topic
                        topic_counts[topic] = topic_counts.get(topic, 0) + 1

                except KeyError as e:
                    self.stdout.write(self.style.ERROR(f"Row {row_num}: Missing column '{e}'"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Row {row_num}: Error: {e}"))

        if unknown_levels:
            self.stdout.write(self.style.WARNING(f"Unknown levels defaulted to 'Low': {sorted(unknown_levels)}"))

        if topic_counts:
            sorted_topics = dict(sorted(topic_counts.items(), key=lambda x: x[1], reverse=True))
            self.stdout.write(
                self.style.SUCCESS(
                    f'Loaded {loaded_count} new questions across {len(sorted_topics)} topics: {sorted_topics}'
                )
            )
        else:
            self.stdout.write(self.style.WARNING('No questions loaded.'))