import io
import datetime
import base64

from otree.channels.consumers import ExportData, settings, logger, export_wide

from .views import ExportAppExtension, _export_xlsx, _export_csv


class ExportDataChannelsExtension(ExportData):
    def post_receive(self, content: dict):
        """
        if an app name is given, export the app.
        otherwise, export all the data (wide).
        don't need time_spent or chat yet, they are quick enough
        """

        if not content.get('custom'):
            return super().post_receive(content)

        # authenticate
        # maybe it should be is_superuser or something else more specific
        # but this is to be consistent with the rest of Django's login
        if settings.AUTH_LEVEL and not self.message.user.is_authenticated:
            logger.warning(
                'rejected access to data export through non-authenticated '
                'websocket'
            )
            return

        file_extension = content['file_extension']
        app_name = content.get('app_name')

        if file_extension == 'xlsx':
            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            IOClass = io.BytesIO
        else:
            mime_type = 'text/csv'
            IOClass = io.StringIO

        iso_date = datetime.date.today().isoformat()
        with IOClass() as fp:
            if app_name:
                rows = ExportAppExtension.get_data_rows_for_app(app_name)

                if file_extension == 'xlsx':
                    _export_xlsx(fp, rows)
                else:
                    _export_csv(fp, rows)

                file_name_prefix = app_name
            else:
                export_wide(fp, file_extension=file_extension)
                file_name_prefix = 'all_apps_wide'
            data = fp.getvalue()

        file_name = '{}_{}.{}'.format(
            file_name_prefix, iso_date, file_extension)

        if file_extension == 'xlsx':
            data = base64.b64encode(data).decode('utf-8')

        content.update({
            'file_name': file_name,
            'data': data,
            'mime_type': mime_type,
        })
        self.send(content)
