#!/usr/bin/env python3

import praw
import requests


try:
    from credentials import *  # NOQA
except:
    USERNAME = 'someuser'
    PASSWORD = 'somepass'


class Bot(object):
    def __init__(self, username, password):
        self.r = praw.Reddit('/u/{} running ban_pruner.py'.format(USERNAME))
        self.r.login(username, password)
        self.unbanned = []  # internal list of people already unbanned

    def accept_mod_invites(self):
        '''Accepts moderator invites.'''

        for message in self.r.get_unread():
            message.mark_as_read()
            # just assume every message in the inbox is a mod-invite
            try:
                self.r.accept_moderator_invite(message.subreddit.display_name)
            except praw.errors.InvalidInvite:
                pass

    def prune_bans(self, subreddit):
        '''Function that returns names of unbanned users.  The first returned value is
        the intial number of bans.'''
        banned = [i for i in subreddit.get_banned()]
        output = [len(banned)]
        for user in banned:
            if user.name in self.unbanned:
                subreddit.unban(user)
                output.append(user.name)
            else:
                u = requests.get('http://reddit.com/u/{}'.format(user.name))
                if u.status_code == 404:
                    subreddit.remove_ban(user.name)
                    self.unbanned.append(user.name)
                    output.append(user.name)
        return output

    def process_subreddit(self, subreddit):
        '''Processes the ban list and then messages the moderators the summary.'''

        unbanned = [i for i in self.prune_bans(subreddit)]
        banned_count = unbanned[0]
        unbanned_count = len(unbanned[1:])
        bans_left = banned_count - unbanned_count
        message = (
            "I've just completed pruning your ban list, so here's a summary of what I've removed:"
            "\n\n{}\n\n   Your subreddit had a total of {} bans. {} of them were shadowbanned or "
            "deleted and were removed from the list.  You now have {} bans.")
        if unbanned_count == 0:
            summary = ""
        else:
            summary = "\n\n".join(['1. /u/{}'.format(i) for i in unbanned[1:]])
        self.r.send_message(
            subreddit, 'Pruned Bans', message.format(
                summary, banned_count, unbanned_count, bans_left))

    def run(self):
        self.accept_mod_invites()
        for subreddit in self.r.get_my_moderation():
            if subreddit.display_name != self.r.user.name:
                self.process_subreddit(subreddit)
                subreddit.remove_moderator(self.r.user.name)

if __name__ == '__main__':
    bot = Bot(USERNAME, PASSWORD)
    bot.run()
