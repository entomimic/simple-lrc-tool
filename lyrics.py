import asyncio
import platform
import datetime
import re
from datetime import timedelta
from typing import Dict, Any

from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as GSMTCSM
from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSession as GSMTCS
from lrclib import LrcLibAPI

CACHE_DIR = ".lyrics_cache"

def safe_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip()

class Local:
    """
    Was using the name of spotify window, but splitting the name was too complicated.
    SO
    """

    async def get_current_media_info(self) -> Dict[str, Any] | None:
        manager = await GSMTCSM.request_async()
        cur_session = manager.get_current_session()

        if not cur_session:
            print("No current session.")
            return None

        source_app = cur_session.source_app_user_model_id.lower()
        if "spotify" not in source_app:
            print(f"Found media player: '{source_app}', but it's not Spotify")
            # TODO: support other media players
            return None

        properties = await cur_session.try_get_media_properties_async()

        timeline = cur_session.get_timeline_properties()

        cached_position_timedelta = timeline.position
        last_updated_offset = timeline.last_updated_time
        last_updated_dt = last_updated_offset
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        time_passed = (now_dt - last_updated_dt)
        playback_status = manager.get_current_session().get_playback_info().playback_status
        actual_position = cached_position_timedelta
        if playback_status == 4:  # playing
            actual_position = cached_position_timedelta + time_passed
        print(f"Cached time: {cached_position_timedelta} | Real time: {actual_position}")

        duration_seconds = timeline.end_time.seconds
        duration_timedelta = timeline.end_time
        #duration_seconds = duration_seconds / 10_000_000

        info = {
            "title": properties.title,
            "artist": properties.artist,
            "album": properties.album_title,
            "duration_seconds": int(duration_seconds), # for
            "position_timedelta": actual_position,
            "duration_timedelta": duration_timedelta,
        }
        return info

    def fetch_lyrics_from_cache(self, info) -> list[str] | None:
        pass

    def fetch_lyrics(self, info) -> list[str]:
        # test
        print("Fetching lyrics...")
        title = info.get("title")
        artist = info.get("artist")
        album = info.get("album")
        duration_seconds = info.get("duration_seconds")

        api = LrcLibAPI(user_agent="my-app/0.0.1")

        # Get lyrics for a track
        try:
            lyrics = api.get_lyrics(
                track_name=title,
                artist_name=artist,
                album_name=album,
                duration=duration_seconds,
            )
        except Exception as e:
            return ["[00:00.00] ♪"]

        found_lyrics = lyrics.synced_lyrics or lyrics.plain_lyrics
        #print("\n".join(found_lyrics.split("\n")[:5]))
        lyrics_list = found_lyrics.split("\n")

        print("Successfully fetched lyrics")
        return lyrics_list

    def process_lyrics(self, lyrics_list) -> Dict[timedelta, str]:
        # [00:36.34] You'll take my life, but I'll take yours too
        # 0123456789       2nd to 9th
        dict_time_to_lyrics: Dict[timedelta, str] = {}

        for l in lyrics_list:

            if not (
                len(l) >= 10
                and l[0] == "["
                and l[9] =="]"
            ):   # HACK: uhh
                continue

            try:
                # HACK: uhh
                time_str = l[1:9]                              # 00:36.34
                lyric = l[11:] if l[10] == " " else l[10:]     # You'll take my life, but I'll take yours too
                minutes, rests = time_str.split(":")
                seconds, milliseconds = rests.split(".")
                td = timedelta(
                    minutes=int(minutes),
                    seconds=int(seconds),
                    microseconds=int(milliseconds) * 10000, # important
                )
                dict_time_to_lyrics[td] = lyric
                #print(dict_time_to_lyrics)

            except Exception as e:
                print("failed for some reason")
                continue

        return dict_time_to_lyrics

    def match_current_lyrics(self, info, time_to_lyric: Dict[timedelta, str]) -> str:
        """
        to be optimized
        """
        lyric = "♪"

        if time_to_lyric == {}:
            return lyric

        position_timedelta = info.get("position_timedelta")
        lyric_position = info.get("position_timedelta")
        for t in time_to_lyric.keys():
            if position_timedelta >= t:
                lyric_position = t
                #print("11")
            else:
                lyric = time_to_lyric.get(lyric_position, "♪")
                break

        return lyric


async def main_loop() -> None:

    local = Local()
    info = await local.get_current_media_info()
    cur = (info.get("title"), info.get("artist"))
    last = cur
    lyrics = local.fetch_lyrics(info)
    time_to_lyric = local.process_lyrics(lyrics)

    while True:
        print("Checking...")

        local = Local()
        info = await local.get_current_media_info()
        cur = (info.get("title"), info.get("artist"))

        if cur != last:
            last = cur
            lyrics = local.fetch_lyrics(info)
            time_to_lyric = local.process_lyrics(lyrics)
            #print(time_to_lyric)

        if info:
            #print({info["position_timedelta"]: 1})
            print(f"Now Playing: {info['title']} • {info['artist']} ({info['position_timedelta']}/{info['duration_timedelta']})\n{info['album']}")
            lyric_line = local.match_current_lyrics(info, time_to_lyric)
            if lyric_line == "":
                lyric_line = "♪"
            print(lyric_line)

        else:
            print("Not playing")

        await asyncio.sleep(3)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("Exiting...")
    # local = Local()
    # info = local.get_current_media_info()
    # print(info)