   /// @description 

hspeed_ = 0;
vspeed_ = 0;
gravity_ = .5;
acceleration_ = 1;
jump_height_ = -10;
max_hspeed_ = 5;
friction_ = .3;

//map the keys 
keyboard_set_map(ord("D"), vk_right);
keyboard_set_map(ord("W"), vk_up);
keyboard_set_map(ord("A"), vk_left);
keyboard_set_map(ord("S"), vk_down);

//Bullet Cooldown
bullet_cooldown_ = room_speed/4 ;
alarm[0] = bullet_cooldown_;

//Scale Variables
x_scale_ = image_xscale;
y_scale_ = image_yscale;