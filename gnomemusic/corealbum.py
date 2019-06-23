import gi
gi.require_version('Grl', '0.3')
from gi.repository import Gio, Grl, GObject

from gnomemusic import log
from gnomemusic.grilo import grilo
import gnomemusic.utils as utils


class CoreAlbum(GObject.GObject):
    """Exposes a Grl.Media with relevant data as properties
    """

    artist = GObject.Property(type=str)
    composer = GObject.Property(type=str, default=None)
    duration = GObject.Property(type=int, default=0)
    media = GObject.Property(type=Grl.Media)
    selected = GObject.Property(type=bool, default=False)
    title = GObject.Property(type=str)
    year = GObject.Property(type=str, default="----")

    @log
    def __init__(self, media, coremodel):
        super().__init__()

        self._coremodel = coremodel
        self._model = None
        self.update(media)

    @log
    def update(self, media):
        self.props.media = media
        self.props.artist = utils.get_artist_name(media)
        self.props.composer = media.get_composer()
        self.props.title = utils.get_media_title(media)
        self.props.year = utils.get_media_year(media)

    @GObject.Property(
        type=Gio.ListModel, default=None, flags=GObject.ParamFlags.READABLE)
    def model(self):
        if self._model is None:
            self._model = self._coremodel.get_album_model(self.props.media)
            self._model.connect("items-changed", self._on_list_items_changed)

        self._on_list_items_changed(self._model, None, None, None)

        return self._model

    def _on_list_items_changed(self, model, pos, removed, added):
        for coredisc in model:
            coredisc.connect("notify::duration", self._on_duration_changed)

    def _on_duration_changed(self, coredisc, duration):
        duration = 0

        for coredisc in self.props.model:
            duration += coredisc.props.duration

        self.props.duration = duration