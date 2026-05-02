/// @description draws the gun and player

var dir = point_direction(x, y, mouse_x, mouse_y)
var flipped = (mouse_x > x)*2-1;

//Draws the Player
draw_sprite_ext(spr_player, 0, x, y, x_scale_*flipped, y_scale_, 0, image_blend, image_alpha);

//draws the gun
draw_sprite_ext(spr_gun, 0, x-3*flipped, y-sprite_height/2, 1, flipped, dir, image_blend, image_alpha);


 