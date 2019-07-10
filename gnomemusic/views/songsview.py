# Copyright (c) 2016 The GNOME Music Developers
#
# GNOME Music is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# GNOME Music is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with GNOME Music; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# The GNOME Music authors hereby grant permission for non-GPL compatible
# GStreamer plugins to be used and distributed together with GStreamer
# and GNOME Music.  This permission is above and beyond the permissions
# granted by the GPL license by which GNOME Music is covered.  If you
# modify this code, you may extend this exception to your version of the
# code, but you are not obligated to do so.  If you do not wish to do so,
# delete this exception statement from your version.

import logging
from gettext import gettext as _
from gi.repository import Gdk, Gtk, Pango

from gnomemusic import log
from gnomemusic.player import PlayerPlaylist
from gnomemusic.views.baseview import BaseView
import gnomemusic.utils as utils

logger = logging.getLogger(__name__)


class SongsView(BaseView):
    """Main view of all songs sorted artistwise

    Consists all songs along with songname, star, length, artist
    and the album name.
    """

    def __repr__(self):
        return '<SongsView>'

    @log
    def __init__(self, window, player):
        """Initialize

        :param GtkWidget window: The main window
        :param player: The main player object
        """
        self._window = window
        self._coremodel = self._window._app.props.coremodel
        super().__init__('songs', _("Songs"), window)

        self._offset = 0
        self._iter_to_clean = None

        self._view.get_style_context().add_class('songs-list-old')

        self._add_list_renderers()

        self._playlist_model = self._coremodel.props.playlist_sort

        self.player = player
        self.player.connect('song-changed', self._update_model)
        self.player.connect('song-validated', self._on_song_validated)

        self._model = self._view.props.model
        self._view.show()

    @log
    def _setup_view(self):
        view_container = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self._box.pack_start(view_container, True, True, 0)

        self._view = Gtk.TreeView()
        self._view.props.headers_visible = False
        self._view.props.valign = Gtk.Align.START
        self._view.props.model = self._coremodel.props.songs_gtkliststore
        self._view.props.activate_on_single_click = True

        self._ctrl = Gtk.GestureMultiPress().new(self._view)
        self._ctrl.props.propagation_phase = Gtk.PropagationPhase.CAPTURE
        self._ctrl.connect("released", self._on_view_clicked)

        self._view.get_selection().props.mode = Gtk.SelectionMode.SINGLE
        self._view.connect('row-activated', self._on_item_activated)

        view_container.add(self._view)

    @log
    def _add_list_renderers(self):
        now_playing_symbol_renderer = Gtk.CellRendererPixbuf(
            xpad=0, xalign=0.5, yalign=0.5)
        column_now_playing = Gtk.TreeViewColumn()
        column_now_playing.props.fixed_width = 48
        column_now_playing.pack_start(now_playing_symbol_renderer, False)
        column_now_playing.set_cell_data_func(
            now_playing_symbol_renderer, self._on_list_widget_icon_render,
            None)
        self._view.append_column(column_now_playing)

        selection_renderer = Gtk.CellRendererToggle()
        column_selection = Gtk.TreeViewColumn(
            "Selected", selection_renderer, active=6)
        column_selection.props.visible = False
        column_selection.props.fixed_width = 48
        self._view.append_column(column_selection)

        title_renderer = Gtk.CellRendererText(
            xpad=0, xalign=0.0, yalign=0.5, height=48,
            ellipsize=Pango.EllipsizeMode.END)
        column_title = Gtk.TreeViewColumn("Title", title_renderer, text=2)
        column_title.props.expand = True
        self._view.append_column(column_title)

        column_star = Gtk.TreeViewColumn()
        self._view.append_column(column_star)
        self._star_handler.add_star_renderers(column_star)

        duration_renderer = Gtk.CellRendererText(xpad=32, xalign=1.0)
        column_duration = Gtk.TreeViewColumn()
        column_duration.pack_start(duration_renderer, False)
        column_duration.set_cell_data_func(
            duration_renderer, self._on_list_widget_duration_render, None)
        self._view.append_column(column_duration)

        artist_renderer = Gtk.CellRendererText(
            xpad=32, ellipsize=Pango.EllipsizeMode.END)
        column_artist = Gtk.TreeViewColumn("Artist", artist_renderer, text=3)
        column_artist.props.expand = True
        self._view.append_column(column_artist)

        album_renderer = Gtk.CellRendererText(
            xpad=32, ellipsize=Pango.EllipsizeMode.END)
        column_album = Gtk.TreeViewColumn()
        column_album.props.expand = True
        column_album.pack_start(album_renderer, True)
        column_album.set_cell_data_func(
            album_renderer, self._on_list_widget_album_render, None)
        self._view.append_column(column_album)

    def _on_list_widget_duration_render(self, col, cell, model, itr, data):
        item = model[itr][5]
        if item:
            seconds = item.props.duration
            track_time = utils.seconds_to_string(seconds)
            cell.props.text = '{}'.format(track_time)

    def _on_list_widget_album_render(self, coll, cell, model, _iter, data):
        if not model.iter_is_valid(_iter):
            return

        item = model[_iter][5]
        if item:
            cell.props.text = item.props.album

    def _on_list_widget_icon_render(self, col, cell, model, itr, data):
        current_song = self.player.props.current_song
        if current_song is None:
            return

        if model[itr][5].props.grlid == current_song.props.grlid:
            cell.props.icon_name = self._now_playing_icon_name
            cell.props.visible = True
        else:
            cell.props.visible = False

    @log
    def _on_changes_pending(self, data=None):
        if (self._init
                and not self.props.selection_mode):
            self.model.clear()
            self._offset = 0
            self._populate()
            # grilo.changes_pending['Songs'] = False

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        super()._on_selection_mode_changed(widget, data)

        cols = self._view.get_columns()
        cols[1].props.visible = self.props.selection_mode

        if not self.props.selection_mode:
            self._on_changes_pending()

    @log
    def _on_item_activated(self, treeview, path, column):
        """Action performed when clicking on a song

        clicking on star column toggles favorite
        clicking on an other columns launches player

        :param Gtk.TreeView treeview: self._view
        :param Gtk.TreePath path: activated row index
        :param Gtk.TreeViewColumn column: activated column
        """
        if self._star_handler.star_renderer_click:
            self._star_handler.star_renderer_click = False
            return

        if self.props.selection_mode:
            return

        itr = self._view.props.model.get_iter(path)
        coresong = self._view.props.model[itr][5]
        self._window._app._coremodel.set_playlist_model(
            PlayerPlaylist.Type.SONGS, self._view.props.model)

        self.player.play(coresong)

    @log
    def _on_view_clicked(self, gesture, n_press, x, y):
        """Ctrl+click on self._view triggers selection mode."""
        _, state = Gtk.get_current_event_state()
        modifiers = Gtk.accelerator_get_default_mod_mask()
        if (state & modifiers == Gdk.ModifierType.CONTROL_MASK
                and not self.props.selection_mode):
            self.props.selection_mode = True

        # FIXME: In selection mode, star clicks might still trigger
        # activation.
        if self.props.selection_mode:
            path, col, cell_x, cell_y = self._view.get_path_at_pos(x, y)
            iter_ = self._view.props.model.get_iter(path)
            self._model[iter_][6] = not self._model[iter_][6]
            self._model[iter_][5].props.selected = self._model[iter_][6]

    @log
    def _update_model(self, player):
        """Updates model when the song changes

        :param Player player: The main player object
        """
        if self._iter_to_clean:
            self._view.props.model[self._iter_to_clean][10] = False

        index = self.player.props.position
        current_coresong = self._playlist_model[index]
        for idx, liststore in enumerate(self._view.props.model):
            if liststore[5] == current_coresong:
                break

        iter_ = self._view.props.model.get_iter_from_string(str(idx))
        path = self._view.props.model.get_path(iter_)
        self._view.props.model[iter_][10] = True
        self._view.scroll_to_cell(path, None, True, 0.5, 0.5)

        if self._view.props.model[iter_][8] != self._error_icon_name:
            self._iter_to_clean = iter_.copy()

        return False

    @log
    def _on_song_validated(self, player, index, status):
        if not player.playing_playlist(PlayerPlaylist.Type.SONGS, None):
            return

        iter_ = self.model.get_iter_from_string(str(index))
        self.model[iter_][11] = status

    @log
    def _populate(self, data=None):
        """Populates the view"""
        self._init = True

    def _select(self, value):
        with self._model.freeze_notify():
            itr = self._model.iter_children(None)
            while itr is not None:
                self._model[itr][5].props.selected = value
                self._model[itr][6] = value

                itr = self._model.iter_next(itr)

    def select_all(self):
        self._select(True)

    def unselect_all(self):
        self._select(False)
