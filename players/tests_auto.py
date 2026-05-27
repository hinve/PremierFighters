from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from teams.models import Team
from .models import Player

User = get_user_model()


class PlayerDetailViewTest(TestCase):
    def setUp(self):
        # usuario admin para evitar problemas de permisos
        self.user = User.objects.create_user(username="admin", password="pass", role="admin")
        self.team = Team.objects.create(name="Equipo Test")
        self.player = Player.objects.create(nickname="hinve#4431", real_name="Hinve", team=self.team)
        self.client.force_login(self.user)

    def test_player_detail_status_and_content(self):
        url = reverse("player_detail", args=[self.player.id]) # type: ignore
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.player.nickname)
        self.assertContains(resp, self.team.name)
