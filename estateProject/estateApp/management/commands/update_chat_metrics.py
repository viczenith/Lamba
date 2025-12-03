from django.core.management.base import BaseCommand
from estateApp.models import Message
from estateApp.encryption_utils import ChatEncryption


class Command(BaseCommand):
    help = 'Encrypt all existing messages with company-specific keys'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be encrypted without actually encrypting',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        messages = Message.objects.filter(is_encrypted=False, company__isnull=False)
        total = messages.count()
        self.stdout.write(f'Found {total} unencrypted messages...')
        
        if dry_run:
            self.stdout.write('DRY RUN - No messages will be encrypted')
            return
        
        encrypted_count = 0
        for message in messages:
            if message.content:
                try:
                    message.content = ChatEncryption.encrypt_message(
                        message.content, 
                        message.company.id
                    )
                    message.is_encrypted = True
                    message.save()
                    encrypted_count += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Failed to encrypt message {message.id}: {e}')
                    )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully encrypted {encrypted_count} messages')
        )