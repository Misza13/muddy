import re

from muddylib.plugins import MuddyPlugin, IncomingTextHandler


class AardwolfStatsPlugin(MuddyPlugin):
    stats_rx = re.compile("""^({stats})
        (?P<i_curr_str>\\d+)/(?P<i_base_str>\\d+),
        (?P<i_curr_int>\\d+)/(?P<i_base_int>\\d+),
        (?P<i_curr_wis>\\d+)/(?P<i_base_wis>\\d+),
        (?P<i_curr_dex>\\d+)/(?P<i_base_dex>\\d+),
        (?P<i_curr_con>\\d+)/(?P<i_base_con>\\d+),
        (?P<i_curr_luck>\\d+)/(?P<i_base_luck>\\d+),
        (?P<i_hp_pct>\\d+),(?P<i_mp_pct>\\d+),(?P<i_mv_pct>\\d+),
        (?P<i_hit_roll>\\d+),(?P<i_dam_roll>\\d+),
        (?P<position>[^,]*),
        (?P<i_enemy_pct>\\d+),
        (?P<i_curr_hp>\\d+)/(?P<i_max_hp>\\d+),
        (?P<i_curr_mp>\\d+)/(?P<i_max_mp>\\d+),
        (?P<i_curr_mv>\\d+)/(?P<i_max_mv>\\d+),
        (?P<i_gold>\\d+),
        (?P<i_qp>\\d+),(?P<i_tp>\\d+),
        (?P<i_align>\\d+),
        (?P<i_tnl>\\d+),
        (?P<i_level>\\d+),
        (?P<i_position_num>\\d+)
        $""", re.VERBOSE)
    
    @IncomingTextHandler
    def handle(self, line):
        stats_m = self.stats_rx.search(line)
        if stats_m:
            stats = StatsParser(stats_m)
            self.invoke_method('StatsWindow', 'set_text', text=[
                f'H: {stats.curr_hp}/{stats.max_hp}',
                f'M: {stats.curr_mp}/{stats.max_mp}',
                f'V: {stats.curr_mv}/{stats.max_mv}',
                '',
                f'E: {stats.enemy_pct}' if stats.enemy_pct < 9999 else '',
                '',
                stats.position
                ])
            return True

        return False


class StatsParser:
    def __init__(self, match):
        self.data = {}
        for k, v in match.groupdict().items():
            if k.startswith('i_'):
                self.data[k[2:]] = int(v)
            else:
                self.data[k] = v
    
    def __getattr__(self, name):
        if name in self.data:
            return self.data[name]
        else:
            return None
