from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Update a user phone and address by id or email (safe - will not update multiple matches).'

    def add_arguments(self, parser):
        parser.add_argument('--id', type=int, help='User id to update')
        parser.add_argument('--email', type=str, help='User email (substring match)')
        parser.add_argument('--phone', type=str, required=True, help='New phone number')
        parser.add_argument('--address', type=str, required=True, help='New address')
        parser.add_argument('--dry-run', action='store_true', help='Show changes but do not save')

    def handle(self, *args, **options):
        User = get_user_model()
        user_qs = None

        if options.get('id'):
            user_qs = User.objects.filter(id=options['id'])
        elif options.get('email'):
            user_qs = User.objects.filter(email__icontains=options['email'])
        else:
            raise CommandError('Provide --id or --email to identify the user')

        count = user_qs.count()
        if count == 0:
            raise CommandError('No users found matching the criteria')
        if count > 1:
            self.stdout.write(self.style.ERROR(f'Multiple users found ({count}). Aborting to avoid unintended updates.'))
            for u in user_qs:
                self.stdout.write(f' - id={u.id} email={u.email} phone={getattr(u, "phone", None)} address={getattr(u, "address", None)} full_name={getattr(u, "full_name", None)}')
            self.stdout.write('Rerun with a specific --id for the intended user.')
            return

        user = user_qs.first()

        new_phone = options['phone']
        new_address = options['address']

        self.stdout.write(f'User found: id={user.id} email={user.email} current_phone={getattr(user, "phone", None)} current_address={getattr(user, "address", None)}')
        self.stdout.write(f'Proposed changes -> phone: {new_phone} | address: {new_address}')

        if options.get('dry_run'):
            self.stdout.write(self.style.SUCCESS('Dry-run: no changes applied.'))
            return

        user.phone = new_phone
        user.address = new_address
        user.save()

        self.stdout.write(self.style.SUCCESS(f'Updated user id={user.id} email={user.email}'))
